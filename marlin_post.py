# ***************************************************************************
# *   Copyright (c) 2014 sliptonic <shopinthewoods@gmail.com>               *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   FreeCAD is distributed in the hope that it will be useful,            *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with FreeCAD; if not, write to the Free Software        *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

from __future__ import print_function
import FreeCAD
from FreeCAD import Units
import Path
import argparse
import datetime
import shlex
from PathScripts import PostUtils

TOOLTIP = """
This is a postprocessor file for the Path workbench. It is used to
take a pseudo-gcode fragment outputted by a Path object, and output
real GCode suitable for a linuxcnc 3 axis mill. This postprocessor, once placed
in the appropriate PathScripts folder, can be used directly from inside
FreeCAD, via the GUI importer or via python scripts with:

import linuxcnc_post
linuxcnc_post.export(object,"/path/to/file.ncc","")
"""

now = datetime.datetime.now()

parser = argparse.ArgumentParser(prog="linuxcnc", add_help=False)
parser.add_argument("--no-header", action="store_true", help="suppress header output")
parser.add_argument(
    "--no-comments", action="store_true", help="suppress comment output"
)
parser.add_argument(
    "--line-numbers", action="store_true", help="prefix with line numbers"
)
parser.add_argument(
    "--no-show-editor",
    action="store_true",
    help="don't pop up editor before writing output",
)
parser.add_argument(
    "--precision", default="3", help="number of digits of precision, default=3"
)
parser.add_argument(
    "--translate_drill",
    action="store_true",
    help="translate drill cycles G81, G82, G83 into G0/G1 movements (default)",
)
parser.add_argument(
    "--no-translate_drill",
    action="store_true",
    help="do not translate drill cycles G81, G82, G83 into G0/G1 movements",
)

parser.add_argument(
    "--preamble",
    help='set commands to be issued before the first command, default="G17\nG90"',
)
parser.add_argument(
    "--postamble",
    help='set commands to be issued after the last command, default="M05\nG17 G90\nM2"',
)
parser.add_argument(
    "--inches", action="store_true", help="Convert output for US imperial mode (G20)"
)
parser.add_argument(
    "--modal",
    action="store_true",
    help="Output the Same G-command Name USE NonModal Mode",
)
parser.add_argument(
    "--axis-modal", action="store_true", help="Output the Same Axis Value Mode"
)

TOOLTIP_ARGS = parser.format_help()

# These globals set common customization preferences
OUTPUT_COMMENTS = True
OUTPUT_HEADER = True
OUTPUT_LINE_NUMBERS = False
SHOW_EDITOR = True
MODAL = False  # if true commands are suppressed if the same as previous line.
OUTPUT_DOUBLES = (
    False  # if false duplicate axis values are suppressed if the same as previous line.
)
COMMAND_SPACE = " "
LINENR = 100  # line number starting value
SUPPRESS_COMMANDS = [""]  # These commands are ignored by commenting them out
MOTION_MODE = "G55"  # G90 only, for absolute moves
MOTION_COMMANDS = ["G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03"]
RAPID_MOVES = ["G0", "G00"]  # Rapid moves gcode commands definition

DRILL_RETRACT_MODE = "G98"  # End of drill-cycle retractation type. G99
# is the alternative.
TRANSLATE_DRILL_CYCLES = True  # If true, G81, G82, and G83 are translated
# into G0/G1 moves

# These globals will be reflected in the Machine configuration of the project
UNITS = "G21"  # G21 for metric, G20 for us standard
UNIT_SPEED_FORMAT = "mm/min"
UNIT_FORMAT = "mm"

MACHINE_NAME = "MarlinCNC"
CORNER_MIN = {"x": 0, "y": 0, "z": 0}
CORNER_MAX = {"x": 800, "y": 1270, "z": 50}
PRECISION = 3

# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = """
G90
G17
"""

# Postamble text will appear following the last operation.
POSTAMBLE = """
M400
G S4
M42 M1 P19 S1
M42 M1 P20 S1
G0 X0 Y0
M400
"""

# Pre operation text will be inserted before every operation
PRE_OPERATION = """"""

# Post operation text will be inserted after every operation
POST_OPERATION = """"""

# Tool Change commands will be inserted before a tool change
TOOL_CHANGE = """"""
# Global variables storing current position (Use None for safety.)
CURRENT_X = None
CURRENT_Y = None
CURRENT_Z = None

# to distinguish python built-in open function from the one declared below
if open.__module__ in ["__builtin__", "io"]:
    pythonopen = open


def processArguments(argstring):
    global OUTPUT_HEADER
    global OUTPUT_COMMENTS
    global OUTPUT_LINE_NUMBERS
    global SHOW_EDITOR
    global PRECISION
    global PREAMBLE
    global POSTAMBLE
    global UNITS
    global UNIT_SPEED_FORMAT
    global UNIT_FORMAT
    global TRANSLATE_DRILL_CYCLES
    global MODAL
    global OUTPUT_DOUBLES
    


    try:
        args = parser.parse_args(shlex.split(argstring))
        if args.no_header:
            OUTPUT_HEADER = False
        if args.no_comments:
            OUTPUT_COMMENTS = False
        if args.line_numbers:
            OUTPUT_LINE_NUMBERS = True
        if args.no_show_editor:
            SHOW_EDITOR = False
        print("Show editor = %d" % SHOW_EDITOR)
        PRECISION = args.precision
        if args.preamble is not None:
            PREAMBLE = args.preamble
        if args.postamble is not None:
            POSTAMBLE = args.postamble
        if args.no_translate_drill:
            TRANSLATE_DRILL_CYCLES = False
        if args.translate_drill:
            TRANSLATE_DRILL_CYCLES = True
        if args.inches:
            UNITS = "G20"
            UNIT_SPEED_FORMAT = "in/min"
            UNIT_FORMAT = "in"
            PRECISION = 4
        if args.modal:
            MODAL = True
        if args.axis_modal:
            print("here")
            OUTPUT_DOUBLES = False

    except Exception:
        return False

    return True


def export(objectslist, filename, argstring):
    if not processArguments(argstring):
        return None
    global UNITS
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT
    global SUPPRESS_COMMANDS

    for obj in objectslist:
        if not hasattr(obj, "Path"):
            print(
                "the object "
                + obj.Name
                + " is not a path. Please select only path and Compounds."
            )
            return None

    print("postprocessing...")
    gcode = ""

    # write header
    if OUTPUT_HEADER:
        gcode += linenumber() + "(Exported by FreeCAD)\n"
        gcode += linenumber() + "(Post Processor: " + __name__ + ")\n"
        gcode += linenumber() + "(Output Time:" + str(now) + ")\n"

    # Suppress drill-cycle commands:
    if TRANSLATE_DRILL_CYCLES:
        SUPPRESS_COMMANDS += ["G80", "G98", "G99"]

    # Write the preamble
    if OUTPUT_COMMENTS:
        gcode += linenumber() + "M117(begin preamble)\n"
    for line in PREAMBLE.splitlines(False):
        gcode += linenumber() + line + "\n"
    gcode += linenumber() + UNITS + "\n"

    for obj in objectslist:

        # Skip inactive operations
        if hasattr(obj, "Active"):
            if not obj.Active:
                continue
        if hasattr(obj, "Base") and hasattr(obj.Base, "Active"):
            if not obj.Base.Active:
                continue

        # do the pre_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + "M117 (begin operation: %s)\n" % obj.Label
            gcode += linenumber() + "; (machine units: %s)\n" % (UNIT_SPEED_FORMAT)
        for line in PRE_OPERATION.splitlines(True):
            gcode += linenumber() + line

        # get coolant mode
        coolantMode = "None"
        if (
            hasattr(obj, "CoolantMode")
            or hasattr(obj, "Base")
            and hasattr(obj.Base, "CoolantMode")
        ):
            if hasattr(obj, "CoolantMode"):
                coolantMode = obj.CoolantMode
            else:
                coolantMode = obj.Base.CoolantMode

        # turn coolant on if required
        if OUTPUT_COMMENTS:
            if not coolantMode == "None":
                gcode += linenumber() + "M117(Coolant On:" + coolantMode + ")\n"
        if coolantMode == "Flood":
            gcode += linenumber() + "M8" + "\n"
        if coolantMode == "Mist":
            gcode += linenumber() + "M7" + "\n"

        # process the operation gcode
        gcode += parse(obj)

        # do the post_op
        if OUTPUT_COMMENTS:
            gcode += linenumber() + "M117(finish operation: %s)\n" % obj.Label
        for line in POST_OPERATION.splitlines(True):
            gcode += linenumber() + line

        # turn coolant off if required
        if not coolantMode == "None":
            if OUTPUT_COMMENTS:
                gcode += linenumber() + "M117(Coolant Off:" + coolantMode + ")\n"
            gcode += linenumber() + "M9" + "\n"

    # do the post_amble
    if OUTPUT_COMMENTS:
        gcode += "M117(begin postamble)\n"
    for line in POSTAMBLE.splitlines(True):
        gcode += linenumber() + line

    if FreeCAD.GuiUp and SHOW_EDITOR:
        final = gcode
        if len(gcode) > 1000000:
            print("Skipping editor since output is greater than 100kb")
        else:
            dia = PostUtils.GCodeEditorDialog()
            dia.editor.setText(gcode)
            result = dia.exec_()
            if result:
                final = dia.editor.toPlainText()
    else:
        final = gcode

    print("done postprocessing.")

    if not filename == "-":
        gfile = pythonopen(filename, "w")
        gfile.write(final)
        gfile.close()

    return final


def linenumber():
    global LINENR
    if OUTPUT_LINE_NUMBERS is True:
        LINENR += 10
        return "N" + str(LINENR) + " "
    return ""

def format_outstring(strTable):
    # construct the line for the final output
    global COMMAND_SPACE
    s = ""
    for w in strTable:
        s += w + COMMAND_SPACE
    return s.strip()

def parse(pathobj):
    global DRILL_RETRACT_MODE
    global PRECISION
    global MODAL
    global OUTPUT_DOUBLES
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT
    global MOTION_MODE
    global CURRENT_X
    global CURRENT_Y
    global CURRENT_Z

    out = ""
    lastcommand = None
    precision_string = "." + str(PRECISION) + "f"
    currLocation = {}  # keep track for no doubles

    # the order of parameters
    # linuxcnc doesn't want K properties on XY plane  Arcs need work.
    params = [

        "X",
        "Y",
        "Z",
        "A",
        "B",
        "C",
        "U",
        "V",
        "W",
        "I",
        "J",
        "K",
        "F",
        "S",
        "T",
        "Q",
        "R",
        "L",
        "P",
        "H",
        "D",

    ]
    firstmove = Path.Command("G0", {"X": -1, "Y": -1, "Z": -1, "F": 0.0})
    currLocation.update(firstmove.Parameters)  # set First location Parameters

    if hasattr(pathobj, "Group"):  # We have a compound or project.
        if OUTPUT_COMMENTS:
             out += linenumber() + "(compound: " + pathobj.Label + ")\n"
        for p in pathobj.Group:
            out += parse(p)
        return out
    else:  # parsing simple path
  
        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        if OUTPUT_COMMENTS:
            out += linenumber() + ";Path(" + pathobj.Label + ")\n"
     

        for c in pathobj.Path.Commands:

            outstring = []
            command = c.Name
            outstring.append(command)
            # if modal: suppress the command if it is the same as the last one
            if MODAL is True:
                if command == lastcommand:
                    outstring.pop(0)

            if c.Name[0] == "(" and not OUTPUT_COMMENTS:  # command is a comment
                continue

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == "F" and (
                        currLocation[param] != c.Parameters[param] or OUTPUT_DOUBLES
                    ):
                        if c.Name not in RAPID_MOVES:  # linuxcnc doesn't use rapid speeds
                            speed = Units.Quantity(
                                c.Parameters["F"], FreeCAD.Units.Velocity
                            )
                            if speed.getValueAs(UNIT_SPEED_FORMAT) > 0.0:
                                outstring.append(
                                    param
                                    + format(
                                        float(speed.getValueAs(UNIT_SPEED_FORMAT)),
                                        precision_string,
                                    )
                                )
                        else:
                            continue
                    elif param == "T":
                        outstring.append(param + str(int(c.Parameters["T"])))
                    elif param == "H":
                        outstring.append(param + str(int(c.Parameters["H"])))
                    elif param == "D":
                        outstring.append(param + str(int(c.Parameters["D"])))
                    elif param == "S":
                        outstring.append(param + str(int(c.Parameters["S"])))
                    elif param == "P":
                        outstring.append(param + str(int(c.Parameters["P"])))
                    elif param == "Q":
                        outstring.append(param + str(int(c.Parameters["Q"])))
                    elif param == "R":
                        outstring.append(param + str(int(c.Parameters["R"])))
                    else:
                        if (
                            (not OUTPUT_DOUBLES)
                            and (param in currLocation)
                            and (currLocation[param] == c.Parameters[param])
                        ):
                            continue
                        else:
                            pos = Units.Quantity(
                                c.Parameters[param], FreeCAD.Units.Length
                            )
                            outstring.append(
                                param
                                + format(
                                    float(pos.getValueAs(UNIT_FORMAT)), precision_string
                                )
                            )

            # store the latest command
            lastcommand = command
            currLocation.update(c.Parameters)
            
            if command in MOTION_COMMANDS:
                if "X" in c.Parameters:
                    CURRENT_X = Units.Quantity(c.Parameters["X"], FreeCAD.Units.Length)
                if "Y" in c.Parameters:
                    CURRENT_Y = Units.Quantity(c.Parameters["Y"], FreeCAD.Units.Length)
                if "Z" in c.Parameters:
                    CURRENT_Z = Units.Quantity(c.Parameters["Z"], FreeCAD.Units.Length)

            if command in ("G98", "G99"):
                DRILL_RETRACT_MODE = command

            if TRANSLATE_DRILL_CYCLES:
                if command in ("G81", "G82", "G83"):
                    out += drill_translate(outstring, command, c.Parameters)
                     #Erase the line just translated:
                    outstring = []

            # Check for Tool Change:
            if command in ("M6", "M06"):
                    out += "M400 ; wait till everything ended"
                    out += "\n"
                    out += "M42 M1 P19 S1 ;spindle off"
                    out += "\n"
                    out += "M42 M1 P20 S1 ; vacuum off"
                    out += "\n"
                    out += "G53 ;switch to main coordinate system"
                    out += "\n"
                    out += "G0 Z50;Z0 has to be the heighest the cnc can go."
                    out += "\n"
                    out += "G0 Y100 ; Go Y 100 first"
                    out += "\n"
                    out += "G0 X150 ; Go X 1500 next"
                    out += "\n"
                    out += "G55 ;change to workspace 2"
                    out += "\n"
                    out += "G0 Z0 ;Go to 0 of workspace."
                    out += "\n"
                    out += "M0 Install tool: {}; change bit".format(c.Parameters['T']) 
                    out += "\n"
                    out += "G53 ;switch to main coordinate system"
                    out += "\n"
                    out += "G0 Z50 ;Z has to be the heighest the cnc can go."
                    out += "\n"
                    out += "G55 ;change to workspace 2"
                    out += "\n"
                    out += "G0 Y0 ; Go Y 0 first"
                    out += "\n"
                    out += "G0 X0 ; Go X 0 next"
                    out += "\n"
                    out += "M42 M1 P19 S0 ;spindle on"
                    out += "\n"
                    out += "M42 M1 P20 S0 ; vacuum on"
                    out += "\n"
                    out += "M117 end tool switch"
                    out += "\n"
                    outstring = []
                         
            if command in ("M3", "M03", "M4", "M04"):
                    out += "\n"
                    out += ";(activate Spindle normally M3)"
                    out += "\n"
                    out += "M400"
                    out += "\n"
                    out += "M42 M1 P19 S0"
                    out += "\n"
                    out += "M42 M1 P20 S0"
                    out += "\n"
                    out += "G4 S5 ;wait for spindle "
                    out += "\n"
                    outstring = []
                   
            if command == "message":
                if OUTPUT_COMMENTS is False:
                    out = []
                else:
                    outstring.pop(0)  # remove the command

            if command in SUPPRESS_COMMANDS:
                outstring[0] = ";suppcommands(" + outstring[0]
                outstring[-1] = outstring[-1] + ")"

                
            # prepend a line number and append a newline
            if len(outstring) >= 1:
                if OUTPUT_LINE_NUMBERS:
                    outstring.insert(0, (linenumber()))

                # append the line to the final output
                for w in outstring:
                    out += w + COMMAND_SPACE
                # Note: Do *not* strip `out`, since that forces the allocation
                # of a contiguous string & thus quadratic complexity.
                out += "\n"

        return out

# *****************************************************************************
# * As of Marlin 2.0.7.bugfix, canned drill cycles do not exist.              *
# * The following code converts FreeCAD's canned drill cycles into            *
# * gcode that Marlin can use.                                                *
# *****************************************************************************
def drill_translate(outstring, cmd, params):
    global DRILL_RETRACT_MODE
    global MOTION_MODE
    global CURRENT_X
    global CURRENT_Y
    global CURRENT_Z
    global UNITS
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT
    global PRECISION

    class Drill:  # Using a class is necessary for the nested functions.
        gcode = ""

    strFormat = "." + str(PRECISION) + "f"

    if OUTPUT_COMMENTS:  # Comment the original command
        outstring[0] = ";(" + outstring[0]
        outstring[-1] = outstring[-1] + ")"
        Drill.gcode += linenumber() + format_outstring(outstring) + "\n"

    # Cycle conversion only converts the cycles in the XY plane (G17).
    # --> ZX (G18) and YZ (G19) planes produce false gcode.
    drill_X = Units.Quantity(params["X"], FreeCAD.Units.Length)
    drill_Y = Units.Quantity(params["Y"], FreeCAD.Units.Length)
    drill_Z = Units.Quantity(params["Z"], FreeCAD.Units.Length)
    drill_R = Units.Quantity(params["R"], FreeCAD.Units.Length)
    drill_F = Units.Quantity(params["F"], FreeCAD.Units.Velocity)
    if cmd == "G82":
        drill_DwellTime = params["P"]
    elif cmd == "G83":
        drill_Step = Units.Quantity(params["Q"], FreeCAD.Units.Length)

    # R less than Z is error
    if drill_R < drill_Z:
        Drill.gcode += linenumber() + ";(drill cycle error: R less than Z )\n"
        return Drill.gcode

    # Z height to retract to when drill cycle is done:
    if DRILL_RETRACT_MODE == "G98" and CURRENT_Z > drill_R:
        RETRACT_Z = CURRENT_Z
    else:
        RETRACT_Z = drill_R

    # Z motion nested functions:
    def rapid_Z_to(new_Z):
        Drill.gcode += linenumber() + "G0 Z"
        Drill.gcode += format(float(new_Z.getValueAs(UNIT_FORMAT)), strFormat) + "\n"

    def feed_Z_to(new_Z):
        Drill.gcode += linenumber() + "G1 Z"
        Drill.gcode += format(float(new_Z.getValueAs(UNIT_FORMAT)), strFormat) + " F"
        Drill.gcode += format(float(drill_F.getValueAs(UNIT_SPEED_FORMAT)), ".2f") + "\n"

    # Make sure that Z is not below RETRACT_Z:
    if CURRENT_Z < RETRACT_Z:
        rapid_Z_to(RETRACT_Z)

    # Rapid to hole position XY:
    Drill.gcode += linenumber() + "G0 X"
    Drill.gcode += format(float(drill_X.getValueAs(UNIT_FORMAT)), strFormat) + " Y"
    Drill.gcode += format(float(drill_Y.getValueAs(UNIT_FORMAT)), strFormat) + "\n"

    # Rapid to R:
    rapid_Z_to(drill_R)

    # *************************************************************************
    # * Drill cycles:                                                         *
    # * G80 Cancel the drill cycle                                            *
    # * G81 Drill full depth in one pass                                      *
    # * G82 Drill full depth in one pass, and pause at the bottom             *
    # * G83 Drill in pecks, raising the drill to R height after each peck     *
    # * In preparation for a rapid to the next hole position:                 *
    # * G98 After the hole has been drilled, retract to the initial Z value   *
    # * G99 After the hole has been drilled, retract to R height              *
    # * Select G99 only if safe to move from hole to hole at the R height     *
    # *************************************************************************
    if cmd in ("G81", "G82"):
        feed_Z_to(drill_Z)  # Drill hole in one step
        if cmd == "G82":  # Dwell time delay at the bottom of the hole
            Drill.gcode += linenumber() + "G4 S" + str(drill_DwellTime) + "\n"
            # Marlin uses P for milliseconds, S for seconds, change P to S

    elif cmd == "G83":  # Peck drill cycle:
        chip_Space = drill_Step * 0.5
        next_Stop_Z = drill_R - drill_Step
        while next_Stop_Z >= drill_Z:
            feed_Z_to(next_Stop_Z)  # Drill one peck of depth

            # Set next depth, next_Stop_Z is still at the current hole depth
            if (next_Stop_Z - drill_Step) >= drill_Z:
                # Rapid up to clear chips:
                rapid_Z_to(drill_R)
                # Rapid down to just above last peck depth:
                rapid_Z_to(next_Stop_Z + chip_Space)
                # Update next_Stop_Z to next depth:
                next_Stop_Z -= drill_Step
            elif next_Stop_Z == drill_Z:
                break  # Done
            else:  # More to drill, but less than drill_Step
                # Rapid up to clear chips:
                rapid_Z_to(drill_R)
                # Rapid down to just above last peck depth:
                rapid_Z_to(next_Stop_Z + chip_Space)
                # Dril remainder of the hole depth:
                feed_Z_to(drill_Z)
                break  # Done
    rapid_Z_to(RETRACT_Z)  # Done, retract the drill

    return Drill.gcode
# print(__name__ + " gcode postprocessor loaded.")
