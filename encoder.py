"""
Automatic ASCII Shellcode Subtraction Encoder.

Expands on BUGTREE's z3ncoder, which can encode individual 32 bit
hex addresses, by taking in a full shellcode payload and outputting assembly
Originally written by Elias Augusto
Additional changes by Andres Roldan <aroldan [at] fluidattacks.com>
"""

import argparse
from z3 import *
from colorama import Fore, Back, Style
import re
from textwrap import wrap


def solve(b, bc):
    """BUGTREE's function that sub encodes 32 bit hex addresses in 0xFFFFFFFF format."""
    s = Solver()
    bad_chars = [0x20, 0x80, 0x0A, 0x0D, 0x2F, 0x3A, 0x3F, 0x2E, 0x40]
    bad_chars += bc  # I added ability to specify additional badchars
    x, y, z = BitVecs('x y z', 32)
    variables = [x, y, z]

    for var in variables:
        for k in range(0, 32, 8):
            s.add(Extract(k+7, k, var) > BitVecVal(0x20, 8))
            s.add(ULT(Extract(k+7, k, var), BitVecVal(0x80, 8)))
            for c in bad_chars:
                s.add(Extract(k+7, k, var) != BitVecVal(c, 8))

    s.add(x + y + z == b)

    if not s.check() == sat:  # Added error handling because it didn't previously exist
        print(Fore.GREEN + "Badchars too restrictive, shellcode generation failed. Consider using a different payload, your shellcode is too (mathematically) powerful.")
        exit(0)
    s.model()
    r = []
    for i in s.model():
        r.append(s.model()[i].as_long())

    return r


def normalize(bc):
    """I tried to adapt this into a normalizer."""
    s = Solver()
    bad_chars = [0x20, 0x80, 0x0A, 0x0D, 0x2F, 0x3A, 0x3F, 0x2E, 0x40]
    bad_chars += bc  # To specify additional badchars
    x, y = BitVecs('x y', 32)
    variables = [x, y]

    for var in variables:
        for k in range(0, 32, 8):
            s.add(Extract(k+7, k, var) > BitVecVal(0x20, 8))
            s.add(ULT(Extract(k+7, k, var), BitVecVal(0x80, 8)))
            for c in bad_chars:
                s.add(Extract(k+7, k, var) != BitVecVal(c, 8))

    s.add(x & y == 0)

    if not s.check() == sat:  # Added error handling because it didn't previously exist
        print(Fore.GREEN + "Normalizer incompatible with badchars, consider using the -a flag to enable sub based normalizer or use a custom normalizer (-n)")
        exit(0)
    s.model()
    r = []
    for i in s.model():
        r.append(s.model()[i].as_long())

    return r


def normalize_input_shellcode(shellcode):
    """Normalize the shellcode according to several common input types."""
    shellcode = shellcode.replace(' ', '')
    shellcode = shellcode.replace('\\x', '')
    shellcode = shellcode.replace('\\X', '')
    return shellcode


def hexforml(val):
    vh = hex(val)  # Convert to hex
    vhs = vh[2:]  # Remove '0x'
    vhr = "".join(map(str.__add__, vhs[-2::-2],vhs[-1::-2]))  # A more consise way to reverse every two bytes than I was previously using
    return "\\x" + "\\x".join(a + b for a, b in zip(vhr[::2], vhr[1::2]))  # Insert a \x before every character


parser = argparse.ArgumentParser() #Argument that takes shellcode
parser.add_argument("-s", "--shellcode", type=str,
                    help="Input hex shellcode with a byte length of a multiple of 4 or use -p flag to pad automatically.")
parser.add_argument("-b", "--badchars", type=str,
                    help="Input badchars in comma separated format: -b \"0x01,0x02,0x03\". Note that too many additional badchars may cause code generation to fail. Default badchars (immutable): Any character that's not printable or valid ASCII, 0x00,0x0a,0x0b,0x20,0x3A,0x3F,0x2E,0x40.")
parser.add_argument("-n", "--normalizer", type=str,
                    help="Normalizer automatically adjusts for badchars, but if you cannot use \"and\" instructions, this flag can be used to insert custom, pre-tested instructions to normalize eax in this format: -n \"and eax,0x222222222\\nand eax,0x22222222\". Not compatible with hex shellcode generation. Use at your own risk.") #This flag will not be usable with automatic shellcode generation when it is implemented.
parser.add_argument("-f", "--file", type=str,
                    help="Output file for NASM assembly code. Otherwise, it will appear on the terminal. Format: -f file.asm")
parser.add_argument("-p", "--pad", action="store_true",
                    help="Automatically pads shellcode with nops to ensure length is a multiple of 4.")
parser.add_argument("-a", "--altnorm", action="store_true",
                    help="Uses subtraction instructions to set eax to 0 instead of AND. Not optimal, will increase the size of the shellcode.")
parser.add_argument("-e", "--espsetup", type=str,
                    help="Automatically sets up the stack for you. Format: -e \"0x[current ESP address], 0x[intended ESP address]\". ASLR safe, compatible with relocatable stacks.")
parser.add_argument("-v", "--variable", type=str, help="Variable name of the resulting shellcode. Defaults to 'PAYLOAD'. Needs -m.")
parser.add_argument("-m", "--mlgen", action="store_true",
                    help="Generates hex shellcode in \"\\xff\\xff\\xff...\" format.")
args = parser.parse_args()

if not args.shellcode:  # Exit if no shellcode given
    parser.print_help()
    parser.exit()

scode = normalize_input_shellcode(args.shellcode)

if args.pad:
    if len(scode) % 2 == 0:
        while len(scode) %8 != 0:
            scode += "90"
    else:
        parser.error("Malformed or invalid machine language")

if len(scode) % 8 != 0:  # Exit if shellcode length is less than 4
    parser.error("Shellcode byte length is not a multiple of 4, pad shellcode or use -p flag and retry.")

bdchars = []
if args.badchars:
    bcharstxt = args.badchars.split(",")
    bdchars += [int(x, 16) for x in bcharstxt]

nres = [0, 0]
if (not args.normalizer) and (not args.altnorm):  # Normalizer setup
    nres = normalize(bdchars)  # No need to do extra math if they're using a custom normalizer

if args.mlgen and args.normalizer:
    parser.error("Cannot assemble shellcode when custom normalizer is in use.")

if args.altnorm and args.normalizer:
    parser.error("Cannot use two normalizers.")

splitsc = [''.join(x) for x in zip(*[list(scode[z::8]) for z in range(8)])]  # Split into fours
print(Fore.GREEN+"\nAutomatic ASCII Shellcode Subtraction Encoder")
print(Fore.GREEN+"Written by Elias Augusto")
print(Fore.GREEN+"Based on BUGTREE's z3ncoder, a single address subtraction encoder")
if args.file:
    print(Fore.GREEN+"Assembly output file: "+args.file)
print(Fore.GREEN+"\n--------------------------------------------------------------------\n")

print(Fore.GREEN+"Original shellcode:\n")
print(Fore.WHITE+'\n'.join(splitsc))

rsplit = []
for i in range(0,len(splitsc)):  # split each line of shellcode, reverse each byte
    fsplit = [''.join(x) for x in zip(*[list(splitsc[i][z::2]) for z in range(2)])]
    lsplit = fsplit[::-1]
    rsplit += ''.join(map(str, lsplit))

unsplit = ''.join(rsplit)  # Join rsplit into one string
resplit = [''.join(x) for x in zip(*[list(unsplit[z::8]) for z in range(8)])] #split it into strings of 4 bytes again

for i in range(0, len(resplit)):
    resplit[i] = "0x" + resplit[i]

reversesc = resplit[::-1] #Reverse the order of the elements to push to the stack

# Convert elements of reversesc to integers
reversesc_int = [int(x, 16) for x in reversesc]

print(Fore.GREEN + "\n--------------------------------------------------------------------\n")
print(Fore.GREEN + "Shellcode Reversed and Formatted for Stack:\n")
print(Fore.WHITE + '\n'.join(reversesc))

hexsc = reversesc

# Clean up hexsc list to ensure valid hexadecimal strings
hexsc = [h.replace('\\x', '') for h in hexsc]

reciporical = [None]*len(hexsc)
for i in range(0, len(hexsc)):  # Get the reciprocal of every hex string after converting it to an int
    hexsc[i] = int(hexsc[i], 16)
    f = hexsc[i]
    reciporical[i] = 0xFFFFFFFF - f + 1

precip = reciporical
for i in range(0, len(precip)):
    precip[i] = hex(precip[i]&(2**32-1))  # notice how we're outputting this to terminal but sending the unmodified reciporical to the solver?
    # It's a safety measure, don't want to break what's already working
print(Fore.GREEN+"\n--------------------------------------------------------------------\n")
print(Fore.GREEN+"Reciporical of each chunk:\n")
print(Fore.WHITE+'\n'.join(precip))

print(Fore.GREEN+"\n--------------------------------------------------------------------\n")
print(Fore.GREEN+"Assembly Output")
buffer = ""
if args.file:
    print(Fore.GREEN+"Sent to file: "+args.file+"\n")
    buffer += ";Filename: "+args.file+"\n"
buffer += ";Intel assembly output for NASM\n"
buffer += ";Generated by Automatic ASCII Shellcode Subtraction Encoder\n\n"
buffer += ";Unencoded payload = "+args.shellcode+"\n\n"
if args.badchars:
    buffer += ";Custom badchars: "+args.badchars+"\n\n"
if args.normalizer:
    buffer += ";Custom eax normalizer in use, check if errors occur\n"
if not args.espsetup:
    buffer += ";Note: You still need to set up the stack yourself, you do not have the -e flag on.\n\n"
buffer += "global _start\n_start:\n\n"

if args.espsetup:
    sotext = args.espsetup.split(",")
    espstart = int(sotext[0], 16)
    espend = int(sotext[1], 16)
    soffset = hex((espstart-espend) & (2**32-1))  # Give us the offset we need to subtract from the stack
    espoff = solve(int(soffset, 16), bdchars)  # Find the subtraction instructions that could give us the stack offset we want

    sumCheck = 0
    for h in espoff[-3:]:
        sumCheck += h
    checksum = hex(sumCheck & (2**32-1))  #remove annoying extra byte that sometimes appears and does not effect acccuracy

    buffer += ";========Stack Setup========\n"
    buffer += ";Verified offset: " + checksum + "=" + soffset + "\n\n"
    if args.normalizer:
        norm = args.normalizer.split("\\n")
        for g in range(0, len(norm)):
            buffer += norm[g]
            buffer += "\n"
    elif args.altnorm:
        norm = solve(int("0x0", 16), bdchars)
        for h in norm[-3:]:
            buffer += "sub eax,"+hex(h)+" ;normalize eax for safety\n"
    else:
        buffer += "and eax,"+hex(nres[0])+" ;normalize eax for safety\n"
        buffer += "and eax,"+hex(nres[1])+" ;normalize eax for safety\n"
    buffer += "push esp\n"
    buffer += "pop eax\n"

    for h in espoff[-3:]:
        buffer += "sub eax,"+hex(h)+"\n"

    buffer += "push eax\n"
    buffer += "pop esp\n\n"
buffer += ";=========Decoder=========\n\n"

for i in range(0, len(reciporical)):  # Assembly output
    if precip[i] == '0x0':
        buffer += ";~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
        buffer += ";Line of nulls\n\n"
        if args.normalizer:
            norm = args.normalizer.split("\\n")
            for g in range(0,len(norm)):
                buffer += norm[g]
                buffer += "\n"
        elif args.altnorm:
            norm = solve(int("0x0", 16), bdchars)
            for h in norm[-3:]:
                buffer += "sub eax," + hex(h) + " ;normalize eax\n"
        else:
            buffer += "and eax," + hex(nres[0]) + " ;normalize eax\n"
            buffer += "and eax," + hex(nres[1]) + " ;normalize eax\n"
        buffer += "push eax\n\n"
    else:
        sumCheck = 0
        result = solve(int(reciporical[i],16),bdchars)
        for h in result[-3:]:
            sumCheck += h
        checksum = hex(sumCheck & (2**32-1))  # remove annoying extra byte that sometimes appears and does not effect acccuracy
        buffer += ";~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n"
        buffer += ";0xFFFFFFFF - "+hex(reversesc_int[i])+" + 1 = "+precip[i]+"\n"
        buffer += ";Verified: "+checksum+" = "+precip[i]+"\n\n"
        if args.normalizer:
            norm = args.normalizer.split("\\n")
            for g in range(0,len(norm)):
                buffer += norm[g]
                buffer += "\n"
        elif args.altnorm:
            norm = solve(int("0x0", 16), bdchars)
            for h in norm[-3:]:
                buffer += "sub eax," + hex(h)+ " ;normalize eax\n"
        else:
            buffer += "and eax," + hex(nres[0]) + " ;normalize eax\n"
            buffer += "and eax," + hex(nres[1]) + " ;normalize eax\n"
        for h in result[-3:]:
            buffer += "sub eax," + hex(h) + "\n"
        buffer += "push eax\n\n"
if not args.file:
    print(Fore.WHITE+buffer)

if args.mlgen:
    variable = args.variable or 'PAYLOAD'
    mlbuffer = ""

    if args.espsetup:
        sotext = args.espsetup.split(",")
        espstart = int(sotext[0],16)
        espend = int(sotext[1],16)
        soffset = hex((espstart-espend) & (2**32-1))  # Give us the offset we need to subtract from the stack
        espoff = solve(int(soffset, 16), bdchars)  # Find the subtraction instructions that could give us the stack offset we want

        if args.altnorm:
            norm = solve(int("0x0", 16),bdchars)
            for h in norm[-3:]:
                mlbuffer += "\\x2d"+hexforml(h)  # sub
        else:
            mlbuffer += "\\x25"+hexforml(nres[0])  # add
            mlbuffer += "\\x25"+hexforml(nres[1])
        mlbuffer += "\\x54"  # push esp
        mlbuffer += "\\x58"  # pop eax

        for h in espoff[-3:]:
            mlbuffer += "\\x2d"+hexforml(h)  # sub

        mlbuffer += "\\x50"  # push eax
        mlbuffer += "\\x5C"  # pop esp

    for i in range(0, len(reciporical)):  # Assembly output
        if precip[i] == '0x0':
            if args.altnorm:
                norm = solve(int("0x0", 16), bdchars)
                for h in norm[-3:]:
                    mlbuffer += "\\x2d" + hexforml(h)  # sub
            else:
                mlbuffer += "\\x25"+hexforml(nres[0])  # add
                mlbuffer += "\\x25"+hexforml(nres[1])
            mlbuffer += "\\x50"  # push eax
        else:
            result = solve(int(reciporical[i], 16), bdchars)
            if args.altnorm:
                norm = solve(int("0x0", 16), bdchars)
                for h in norm[-3:]:
                    mlbuffer += "\\x2d"+hexforml(h)  # sub
            else:
                mlbuffer += "\\x25"+hexforml(nres[0])  # sub
                mlbuffer += "\\x25"+hexforml(nres[1])
            for h in result[-3:]:
                mlbuffer += "\\x2d"+hexforml(h)
            mlbuffer += "\\x50"  # push eax
    # Divide into 32 byte strings for easy python printing here
    mlbufff = ""
    if not len(mlbuffer) <= 64:
        mlbufformat = wrap(mlbuffer, 64)
        mlbufff = "'\n{} += b'".format(variable).join(mlbufformat)
    else:
        mlbufff = mlbuffer
    print(Fore.GREEN + "\n--------------------------------------------------------------------\n") #Printing time
    print(Fore.GREEN + "Shellcode length: "+str(int(len(mlbuffer)/4)))
    print(Fore.GREEN + "Shellcode Output:\n")

    print(Fore.WHITE + "{} =  b'".format(variable) + mlbufff+"'" + "\n")

if args.file:
    asmfile = open(args.file, "w")
    asmfile.write(buffer)
    asmfile.close()
