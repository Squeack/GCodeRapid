# GCodeRapid
# Speed up high non-cutting moves to use G0 if they currently use G1
# (C) 2020 Ian Shatwell

import sys
import argparse


def numberfrom(s, p):
    # Find all consecutive numeric characters starting at position p
    # Include 0123456789+-.
    numchars = "0123456789+-."
    retval = ""
    pmax = len(s)
    s += " "
    while p < pmax and numchars.find(s[p]) >= 0:
        retval += str(s[p])
        p += 1
    return retval


current_x = 0
current_y = 0
current_z = 999
current_f = 0
cutf = 0
maxf = 3000
rapidf = maxf
maxlinelen = 65
movetype = 0  # G0 - G3
movemode = 0  # G90 absolute or G91 relative
rapidmove = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-I", "--infile", help="GCode file to read")
    parser.add_argument("-O", "--outfile", help="GCode file to write")
    parser.add_argument("-A", "--annotate", help="GCode file to annotate")
    args = parser.parse_args()
    if not args.infile:
        print("Error! No input file specified")
        sys.exit(1)
    else:
        infile = args.infile
        p = infile.rfind(".")
        if p < 0:
            inbase = infile
            inext = ""
        else:
            inbase = infile[0:p]
            inext = infile[p:]
    if args.outfile:
        outfile = args.outfile
    else:
        outfile = inbase + "_rapid" + inext
    if infile == outfile:
        print("Error! Overwriting input file")
        sys.exit(1)
    if args.annotate:
        annofile = args.annotate
    else:
        annofile = inbase + "_annotate" + inext
    if infile == annofile:
        print("Error! Overwriting input file")
        sys.exit(1)
    print("Reading from", infile)
    if args.annotate:
        print("Annotating", annofile)
    print("Writing to", outfile)

    filein = open(infile, 'r')
    if args.annotate:
        fileanno = open(annofile, 'w')
    fileout = open(outfile, 'w')
    Lines = filein.readlines()
    for lnum in range(len(Lines)):
        inline = Lines[lnum]
        inline = inline.strip()
        if len(inline) == 0:
            continue
        outline = inline
        anno = ""
        iscomment = inline[0] == '('
        if iscomment:
            if len(inline) > maxlinelen:
                anno += " (Too long line)"
                outline = "(Long comment removed)"
            if args.annotate:
                fileanno.write(inline + anno + "\n")
            fileout.write(outline + "\n")
            # Do not process this line any further
            continue
        iscontrol = inline[0] == 'S' or inline[0] == 'M' or inline[0] == 'T'
        if iscontrol:
            if args.annotate:
                fileanno.write(inline + anno + "\n")
            fileout.write(outline + "\n")
            continue
        isg = inline[0] == 'G'
        if isg:
            num = int(numberfrom(inline, 1))
            if  0 <= num <= 3:
                movetype = num
            if num == 90:
                movemode = 0
            if num == 91:
                movemode = 1
            if num == 0: anno += " (Rapid)"
            if num == 1: anno += " (Straight)"
            if num == 2: anno += " (Arc CW)"
            if num == 3: anno += " (Arc CCW)"
            if num == 90: anno += " (Absolute moves)"
            if num == 91: anno += " (Relative moves)"

        xp = inline.find('X')
        yp = inline.find('Y')
        zp = inline.find('Z')
        fp = inline.find('F')
        target_x = current_x
        target_y = current_y
        target_z = current_z
        target_f = current_f
        # Where are we going?
        if xp >= 0:
            xparam = float(numberfrom(inline, xp + 1))
            if movemode == 0:
                target_x = xparam
            else:
                target_x = current_x + xparam
        if yp >= 0:
            yparam = float(numberfrom(inline, yp + 1))
            if movemode == 0:
                target_y = yparam
            else:
                target_y = current_y + yparam
        if zp >= 0:
            zparam = float(numberfrom(inline, zp + 1))
            if movemode == 0:
                target_z = zparam
            else:
                target_z = current_z + zparam

        if fp >= 0:
            # New speed set
            target_f = float(numberfrom(inline, fp + 1))
            if movetype == 0:
                rapidf = target_f
            else:
                cutf = target_f

        # What has changed?
        if target_x != current_x or target_y != current_y:
            # X, Y or both has changed
            if rapidmove:
                anno += " (Should be rapid)"
            if target_z == current_z:
                anno += " (Move in horizontal plane at Z=" + str(current_z) + ")"
            else:
                anno += " (Ramped move)"
        elif target_z > current_z:
            anno += " (Going up)"
            # Do not interfere with explicit G commands in first version
            # Fusion 360 restriction uses G1 at full cutting speed instead of rapid G0
            # Was speed set high as well?
            if not isg and fp >= 0 and target_f >= current_f:
                # Probably start of a rapid, but look at next move
                nextline = Lines[lnum+1]
                if nextline.find('Z') < 0:
                    rapidmove = True
                    anno += " (Move upwards into rapid)"
                    outline = "G0 Z" + str(target_z)  # Ignore F parameter
                else:
                    rapidmove = False
                    anno += " (Move update, but not into rapid)"
        else:
            anno += " (Going down)"
            # Do not interfere with explicit G commands in first version
            if not isg:
                # How far?
                if current_z != 999:
                    downz = current_z - target_z
                    if downz > 1 and rapidmove:
                        # Split into rapid + feed moves
                        anno += " (Down a long way)"
                        newline = "G0 Z" + str(target_z + 1)
                        fileout.write(newline + "\n")
                        outline = "G1 " + outline
                        if fp < 0:
                            outline += " F" + str(cutf)
                        anno += " (End rapid move)"
                        rapidmove = False
                    elif rapidmove:
                        # Small drop
                        outline = "G1 " + outline
                        if fp < 0:
                            outline += " F" + str(cutf)
                        anno += " (End rapid move)"
                        rapidmove = False
        # print(inline,"->",outline)
        if args.annotate:
            fileanno.write(inline + anno + "\n")
        fileout.write(outline + "\n")
        current_x = target_x
        current_y = target_y
        current_z = target_z
        current_f = target_f
