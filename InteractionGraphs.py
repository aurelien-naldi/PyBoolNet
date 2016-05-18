#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
import subprocess
import math
import os
import ConfigParser

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__)))
BASE = os.path.normpath(BASE)
config = ConfigParser.SafeConfigParser()
config.read( os.path.join(BASE, "Dependencies", "settings.cfg") )
CMD_DOT = os.path.join( BASE, "Dependencies", config.get("Executables", "dot") )
CMD_CONVERT = os.path.join( BASE, "Dependencies", config.get("Executables", "convert") )

import networkx

import Utility
dot2image = Utility.dot2image
igraph2cgraph = Utility.digraph2condensationgraph

import StateTransitionGraphs as STGs


def primes2igraph( Primes ):
    """
    Creates the interaction graph from the prime implicants of a network.
    Interaction graphs are implemented as :ref:`installation_networkx` digraph objects.
    Edges are given the attribute *sign* whose value is a Python set containing 1 or -1 or both, depending on
    whether the interaction is activating or inhibiting or both.

    **arguments**:
        * *Primes*: prime implicants

    **returns**:
        * *IGraph* (networkx.DiGraph): interaction graph

    **example**::

            >>> bnet = "\\n".join(["v1, v1","v2, 1", "v3, v1&!v2 | !v1&v2"])
            >>> primes = bnet2primes(bnet)
            >>> igraph = primes2igraph(primes)
            >>> igraph.nodes()
            ['v1', 'v2', 'v3']
            >>> igraph.edges()
            [('v1', 'v1'), ('v1', 'v3'), ('v2', 'v3'), ('v3', 'v1')]
            >>> igraph.edge["v1"]["v3"]["sign"]
            set([1, -1])
    """

    igraph = networkx.DiGraph()
    edges = {}
    for name in Primes:
        igraph.add_node( name )
        for term in Primes[name][1]:
            for k,v in term.items():
                if v==0:
                    sign = -1
                else:
                    sign = +1
                if not (k,name) in edges:
                    edges[(k,name)]=set([])
                edges[(k,name)].add(sign)
                
    for k,name in edges:
        igraph.add_edge( k, name, sign=edges[(k,name)])

    # defaults
    igraph.graph["node"]  = {"style":"filled","shape":"rect","color":"none","fillcolor":"gray95"}
    igraph.graph["edge"]  = {}
    igraph.graph["subgraphs"]  = []
                
    return igraph


def copy( IGraph ):
    """
    Creates a copy of *IGraph* including all *dot* attributes.

    **arguments**:
        * *IGraph*: interaction graph

    **returns**:
        * *IGraph2*: new interaction graph

    **example**::

        >>> igraph2 = copy(igraph)
    """

    newgraph = IGraph.copy()
    if newgraph.graph["subgraphs"]:
        newgraph.graph["subgraphs"] = [x.copy() for x in newgraph.graph["subgraphs"]]

    return newgraph

    
def igraph2dot( IGraph, FnameDOT=None ):
    """
    Generates a *dot* file from *IGraph* and saves it as *FnameDOT* or returns it as a string.
    
    **arguments**:
        * *IGraph*: interaction graph
        * *FnameDOT* (str): name of *dot* file or *None*

    **returns**:
        * *FileDOT* (str): file as string if not *FnameDOT==None*, otherwise it returns *None*

    **example**::

          >>> igraph2dot(igraph, "irma.dot")
          >>> dotfile = igraph2dot(igraph)
    """

    if IGraph.order()==0:
        print "Interaction Graph has no nodes."
        if FnameDOT!=None:
            print FnameDot, "was not created."
        return

    assert( type(IGraph.nodes()[0])==str )
    
    lines = ['digraph "Interaction Graph" {']
    lines+= Utility.digraph2dot( IGraph )
    lines += ['}']

    if FnameDOT==None:
        return '\n'.join(lines)
    
    with open(FnameDOT, 'w') as f:
        f.writelines('\n'.join(lines))
    print "created", FnameDOT


def igraph2image(IGraph, FnameIMAGE, Silent=False):
    """
    Creates an image file from *IGraph* using :ref:`installation_graphviz` and the layout engine *dot*.
    To find out which file formats are supported call ``$ dot -T?``.
    
    **arguments**:
        * *IGraph*: interaction graph
        * *FnameIMAGE* (str): name of image
        * *Silent* (bool): disables print statements
        
    **example**::

          >>> igraph2image( igraph, "mapk_igraph.pdf" )
          >>> igraph2image( igraph, "mapk_igraph.jpg" )
          >>> igraph2image( igraph, "mapk_igraph.svg" )
    """

    assert( FnameIMAGE.count('.')>=1 and FnameIMAGE.split('.')[-1].isalnum() )

    filetype = FnameIMAGE.split('.')[-1]

    cmd = [CMD_DOT, "-T"+filetype, "-o", FnameIMAGE]
    dotfile = igraph2dot( IGraph, FnameDOT=None)
    
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate( input=dotfile )
    proc.stdin.close()

    if not (proc.returncode == 0) or not os.path.exists(FnameIMAGE):
        print out
        print 'dot did not respond with return code 0'
        raise Exception
    
    if not Silent:
        print "created", FnameIMAGE

    
    
def add_style_interactionsigns( IGraph ):
    """
    Sets attributes for the arrow head and edge color of interactions to indicate the interaction sign.
    Activating interactions get the attributes *"arrowhead"="normal"* and *"color"="black"*,
    inhibiting interactions get the attributes *"arrowhead"="tee"* and *"color"="red"*, and
    ambivalent interaction get the attributes *"arrowhead"="dot"* and *"color"="blue"*.
    
    **arguments**:
        * *IGraph*: interaction graph
        
    **example**::

          >>> add_style_interactionsigns(igraph)
    """

    for source, target, attr in sorted(IGraph.edges(data=True)):
        if attr["sign"]==set([1,-1]):
            IGraph.edge[source][target]["arrowhead"] = "dot"
            IGraph.edge[source][target]["color"] = "dodgerblue"
        elif attr["sign"]==set([-1]):
            IGraph.edge[source][target]["arrowhead"] = "tee"
            IGraph.edge[source][target]["color"] = "red"
        elif attr["sign"]==set([1]):
            IGraph.edge[source][target]["arrowhead"] = "normal"
            IGraph.edge[source][target]["color"] = "black"


    
def add_style_activities( IGraph, Activities ):
    """
    Sets attributes for the color and fillcolor of nodes to indicate which variables are activated and which are inhibited in *Activities*.
    All activated or inhibited components get the attribute *"color"="black"*.
    Activated components get the attribute *"fillcolor"="red"* and
    inactivated components get the attribute *"fillcolor"="blue"*.
    Interactions involving activated or inhibited nodes get the attribute *"color"="gray"* to reflect that they are ineffective.
    
    **arguments**:
        * *IGraph*: interaction graph
        * *Activities* (dict): activated and inhibited nodes
        
    **example**::

          >>> activities = {"ERK":1, "MAPK":0}
          >>> add_style_activities(igraph, activities)
    """

    names = sorted(IGraph.nodes())
    if type(Activities)==str:
        Activities = STGs.str2subspace(names, Activities)

    for name in IGraph.nodes():

        # steady variables
        if name in Activities:
            value = Activities[name]
            
            IGraph.node[name]["color"] = "black"
                
            # inactive = blue
            if value == 0:
                IGraph.node[name]["fillcolor"] = "/paired10/1"

            # active = red
            else:
                IGraph.node[name]["fillcolor"] = "/paired10/5"

    for x,y in IGraph.edges():
        if x in Activities or y in Activities:
            IGraph.edge[x][y]["color"] = "gray"
            

def add_style_inputs( IGraph ):
    """
    Adds a subgraph to the *dot* representation of *IGraph* that contains all inputs.
    Nodes that belong to the same *dot* subgraph are contained in a rectangle and treated separately during layout computations.
    In addition, the subgraph is labeled by a *"Inputs"* in bold font.
    
    **arguments**:
        * *IGraph*: interaction graph
        
    **example**::

          >>> add_style_inputs(igraph)
    """

    inputs = [x for x in IGraph.nodes() if IGraph.in_degree(x)==1 and x in IGraph.successors(x)]

    if inputs:
        subgraph = networkx.DiGraph()
        subgraph.add_nodes_from(inputs)
        subgraph.graph["label"] = "<<B>Inputs</B>>"
        subgraph.graph["fontsize"] = "20"
        
        # remove subgraphs for inputs added by add_style_sccs 
        for x in list(IGraph.graph["subgraphs"]):
            y = x.nodes()
            if len(y)==1 and y[0] in inputs:
                IGraph.graph["subgraphs"].remove(x)

        IGraph.graph["subgraphs"].append( subgraph )


def add_style_outputs( IGraph ):
    """
    Adds a subgraph to the *dot* representation of *IGraph* that contains all outputs.
    Nodes that belong to the same *dot* subgraph are contained in a rectangle and treated separately during layout computations.
    In addition, the subgraph is labeled by a *"Outputs"* in bold font.
    
    **arguments**:
        * *IGraph*: interaction graph
        
    **example**::

          >>> add_style_outputs(igraph)
    """

    outputs = [x for x in IGraph.nodes() if not IGraph.successors(x) or IGraph.successors(x)==[x]]
    
    if outputs:
        subgraph = networkx.DiGraph()
        subgraph.add_nodes_from(outputs)
        subgraph.graph["label"] = "<<B>Outputs</B>>"
        subgraph.graph["fontsize"] = "20"
        IGraph.graph["subgraphs"].append( subgraph )
        

def add_style_constants( IGraph ):
    """
    Sets the attribute *"style"="plaintext"* with *"fillcolor"="none"* and *"fontname"="Times-Italic"* for all constants.
    
    **arguments**:
        * *IGraph*: interaction graph
        
    **example**::

          >>> add_style_constants(igraph)
    """

    for x in IGraph.nodes():
        if not IGraph.predecessors(x):
            IGraph.node[x]["shape"] = "plaintext"
            IGraph.node[x]["fillcolor"] = "none"
            IGraph.node[x]["fontname"] = "Times-Italic"

            for y in IGraph.successors(x):
                IGraph.edge[x][y]["color"] = "gray"
                


def add_style_sccs( IGraph ):
    """
    Adds a subgraph for every non-trivial strongly connected component (SCC) to the *dot* representation of *IGraph*.
    Nodes that belong to the same *dot* subgraph are contained in a rectangle and treated separately during layout computations.
    Each subgraph is filled by a shade of gray that gets darker with an increasing number of SCCs that are above it in the condensation graph.
    Shadings repeat after a depth of 9.

    **arguments**:
        * *IGraph*: interaction graph
        
    **example**::

          >>> add_style_sccs(igraph)
    """
    
    subgraphs = networkx.DiGraph()
    condensation_graph = Utility.digraph2condensationgraph(IGraph)

    for scc in condensation_graph.nodes():
        depth = condensation_graph.node[scc]["depth"]
        col   = 2+(depth % 8)

        subgraph = networkx.DiGraph()
        subgraph.add_nodes_from(scc)
        subgraph.graph["style"] = "filled"
        subgraph.graph["fillcolor"] = "/greys9/%i"%col
        
        IGraph.graph["subgraphs"].append( subgraph )
        


def add_style_condensation( IGraph ):
    """
    Adds a separate graph to *IGraph* that depicts the *condensation graph*, a map of how the SCCs regulate each other.
    A node in the condensation graph indicates how many variables are contained in the respective SCC.
    If the SCC contains a single variable then its name is displayed.
    
    **arguments**:
        * *IGraph*: interaction graph
        
    **example**::

          >>> add_style_condensation(igraph)
    """

    condensation_graph = Utility.digraph2condensationgraph(IGraph)
    IGraph.graph["condensation"] = condensation_graph


def add_style_path( IGraph, Path, Color ):
    """
    Sets the color of all nodes and edges involved in the given *Path* to *Color*.

    **arguments**:
        * *IGraph*: interaction graph
        * *Path* (list): sequence of component names
        * *Color* (str): color of the path
    
    **example**::

        >>> path = ["Raf", "Ras", "Mek"]
        >>> add_style_path(igraph, path, "red")
    """

    if not Path: return

    names = IGraph.nodes()
    assert( all([x in names for x in Path]) )

    for x in Path:
        IGraph.node[x]["color"] = Color
        
    if len(Path)>1:
        for x,y in zip(Path[:-1],Path[1:]):
            IGraph.edge[x][y]["color"]     = Color
            IGraph.edge[x][y]["penwidth"]  = "2"
    

def add_style_subgraphs( IGraph, Subgraphs ):
    """
    Adds the subgraphs given in *Subgraphs* to *IGraph* - or overwrites them if they already exist.
    Nodes that belong to the same *dot* subgraph are contained in a rectangle and treated separately during layout computations.
    To add custom labels or fillcolors to a subgraph supply a tuple consisting of the
    list of nodes and a dictionary of subgraph attributes.

    .. note::
    
        *Subgraphs* must satisfy the following property:
        Any two subgraphs have either empty intersection or one is a subset of the other.
        The reason for this requirement is that *dot* can not draw intersecting subgraphs.

    **arguments**:
        * *IGraph*: interaction graph
        * *Subgraphs* (list): lists of nodes *or* pairs of lists and subgraph attributes

    **example**:

        >>> sub1 = ["v1","v2"]
        >>> sub2 = ["v3","v4"]
        >>> subgraphs = [sub1,sub2]
        >>> add_style_subgraphs(igraph, subgraphs)

        >>> sub1 = (["v1","v2"], {"label":"Genes"})
        >>> sub2 = ["v3","v4"]
        >>> subgraphs = [(sub1,sub2]
        >>> add_style_subgraphs(igraph, subgraphs)
    """

    for x in Subgraphs:

        attr = None
        if len(x)>=2 and type(x[1])==dict:
            nodes, attr = x
        else:
            nodes = x

        if not nodes: continue

        subgraph = networkx.DiGraph()
        subgraph.graph["color"] = "black"
        subgraph.add_nodes_from(nodes)
        if attr:
            subgraph.graph.update(attr)

        # overwrite existing subgraphs
        for x in list(IGraph.graph["subgraphs"]):
            if sorted(x.nodes()) == sorted(subgraph.nodes()):
                IGraph.graph["subgraphs"].remove(x)
                
        IGraph.graph["subgraphs"].append(subgraph)


def add_style_default( IGraph ):
    """
    A convenience function that adds styles for interaction signs, SCCs, inputs, outputs, constants and also the condensation graph.

    **arguments**:
        * *IGraph*: interaction graph
    
    **example**::

        >>> add_style_default(igraph, path)
    
    """

    # careful, the order matters
    add_style_interactionsigns(IGraph)
    add_style_sccs(IGraph)
    add_style_inputs(IGraph)
    add_style_outputs(IGraph)
    add_style_constants(IGraph)
    add_style_condensation(IGraph)




def activities2animation( IGraph, Activities, FnameGIF, FnameTMP="tmp*.jpg", Delay=50, Loop=0 ):
    """
    Generates an animated *gif* from the sequence of *Activities* by mapping the activities on
    the respective components of the interaction graph using :ref:`add_style_activities`.
    The activities may be given in *dict* or *str* format, see :ref:`states_subspaces_paths` for details.
    Requires the program *convert* from the :ref:`installation_imagemagick` software suite.
    The argument *FnameTMP* is the string that is used for generating the individual frames.
    Use "*" to indicate the position of the frame counter.
    The default *"tmp\*.jpg"* will result in the creation of the files::

        tmp01.jpg, tmp02.jpg, ...

    The files will be deleted after the *gif* is generated.
    The *Delay* parameter sets the frame rate and *Loop* the number of repititions,
    both are parameters that are directly passed to *convert*.

    **arguments**.
        * *IGraph*: interaction graph
        * *Activities* (list): sequence of activities
        * *Delay* (int): number of 1/100s between each frame
        * *Loop* (int): number of repetitions, use 0 for infinite
        * *FnameTMP* (str): name for temporary image files, use "*" to indicate counter
        * *FnameGIF* (str): name of the output *gif* file

    **example**::

        >>> activities = ["11--1-0", "111-1-0", "11111-0", "1111100"]
        >>> activities2animation(igraph, activities, "animation.gif")
    """

    assert("." in FnameTMP)
    assert("*" in FnameTMP)
    assert(FnameGIF[-4:].lower()=='.gif')
    assert(Activities != None)

    width = len(str(len(Activities)))+1
    for i,x in enumerate(Activities):
        dummy = copy(IGraph)
        add_style_activities(dummy, x)
        dummy.graph["label"] = "%i of %i"%(i+1,len(Activities))
        igraph2image(IGraph = dummy,
                     FnameIMAGE = FnameTMP.replace("*",'{i:0{w}d}'.format(i=i,w=width)),
                     Silent = True)

    filetype = FnameTMP.split(".")[-1]
    cmd = [CMD_CONVERT, "-delay", str(Delay), "-loop", str(Loop), FnameTMP, FnameGIF]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, error = proc.communicate()

    if not (proc.returncode ==0):
        print output
        print error
        print '"convert" finished with return code %i'%proc.returncode
        print "cmd:",' '.join(cmd)
        raise Exception

    for i in range(len(Activities)):
        fname = FnameTMP.replace("*",'{i:0{w}d}'.format(i=i,w=width))
        os.remove(fname)
    
    print "created", FnameGIF











