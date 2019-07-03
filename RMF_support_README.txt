= Experimental support of RMF files =

Xlink Analyzer can display crosslinks on RMF files, although the RMF support is quite experimental and bugs are expected. 

To enable the RMF support, you have to patch Chimera:
1. Find the share/rmf/ directory in your Chimera installation
    The share directory is located within the Chimera installation folder:
    https://www.cgl.ucsf.edu/chimera/experimental/install.html
    Windows

            C:\Program Files\Chimera\share
    Linux

            /usr/local/chimera/share
    Macintosh

            /Applications/Chimera.app/Contents/Resources/share

    If you still cannot find it, try:
        1. Start Chimera
        2. Open Tools -> General Controls -> IDLE
        3. Type: import rmf and press enter
        4. Type print rmf.__file__ and press enter
        It should print a path to your share folder

1. Download the latest Xlink Analyzer version from ....
1. Replace share/rmf/__init__.py file with XlinkAnalyzer/Chimera_RMF_patch/__init__.py. It includes a patch that adds chain IDs to beads.
1. Open your RMF file and load your Xlink Analyzer project.
 1. Make sure chain IDs in the RMF file match the chain IDs in your XlinkAnalyzer project. Standard IMP and PMI pipelines usually do not preserve chain IDs from input structures.
 1. Display the crosslinks using Xlink Analyzer interface
    1. Note that:
        * an RMF file might load two "models" into Chimera. Model #0.1 is for resolution 0 (e.g. full atom or Calpha), and model #0.2 is for beads. XlinkAnalyzer “sees” both models behind the scenes but displays only #0.1 in its model selection list to avoid users trying to add xlinks to only single of them. So you just select #0.1 and should be fine.
        * Xlink Analyzer will add connectivity lines between beads, so beads that are adjacent in sequence have a dotted line connecting them
        * Sometimes beads are so close to each other that the crosslinks between them are not well visible
