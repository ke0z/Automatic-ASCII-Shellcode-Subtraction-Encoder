
# Automatic ASCII Shellcode Subtraction Encoder
Generates printable ASCII subtraction encoded shellcode in NASM assembly and python hex string format for inserting into exploits.

# Credits
This is a fork of the great work done by Elias Augusto.
This repo will contain several style fixes and some other new features but the core
is the same written by him.

# Opt_Encoder.py
Welcome to the future of...this program! The newly created, highly optimized encoder first tries encoding with one or two sub instructions before attempting the default three. This comes with numerous added benefits, including exponentially shorter payloads and improved badchar resistance.

Nowhere close to opt_sub, but pretty good. It has a lot of default badchars, which accounts for some of that gap, but it's not intelligent enough to know that it doesn't have to normalize EAX after every instruction.

All options are the same as in encoder.py (besides -o), but the help dialogues highlight some differences. To try it out, use:
```
$ python3 opt_encoder.py -s [shellcode] -o -b [badchars] -n [custom eax normalizer] -f [output file] -p -e [esp setup] -m -a
```
This version of the encoder has been tested and accuracy of results have been verified, but due to the fact that a lot of the code has been rewritten I am still labeling it "experimental" until I get more feedback. Both versions will be actively maintained.

# Installation
```
$ git clone https://github.com/EAugustoAnalysis/Automatic-ASCII-Shellcode-Subtraction-Encoder.git
$ cd Automatic-ASCII-Shellcode-Subtraction-Encoder
# pip3 install z3-solver
$ python3 encoder.py
```
Based on Marcos Valle's z3ncoder, which can ASCII encode a 32 bit address:
https://github.com/marcosValle/z3ncoder

# Usage
```
$ python3 encoder.py -s [shellcode] -b [badchars] -n [custom eax normalizer] -f [output file] -p -e [esp setup] -m -a
```
![Help menu updated](ASCII1.1.PNG)

# Example
```
$ python3 encoder.py -s 6681caff0f42526a0258cd2e3c055a74efb8543030578bfaaf75eaaf75e7ffe7
$ python3 encoder.py -s 6681caff0f42526a0258cd2e3c055a74efb8543030578bfaaf75eaaf75e7ffe7 -f egghunter.asm
$ python3 encoder.py -s 6681caff0f42526a0258cd2e3c055a74efb8543030578bfaaf75eaaf75e7ffe7 -b "0x2f,0x41" -n "and eax,0x23232323\nand eax,0x42324543\nand eax, 0x44444444"
$ python3 encoder.py -s 6681caff0f42526a0258cd -p -m #Automatic nop padding enabled, shellcode generated
$ python3 encoder.py -s 6681caff0f42526a0258cd -a #Normalizes with sub instructions
$ python3 encoder.py -s 6681caff0f42526a0258cd -e "0x0x0178ffe9,0x0178ff6a" #Move the ESP from 0x0x0178ffe9 to 0x0178ff6a with subtraction
```
![Example Usage](ASCII2.png)

# Optimized Example
Example payload: windows/shell_reverse_tcp shellcode pre-encoded with x86/fnstenv_mov. Previously tested with multiple unencoded payloads with more modest results (237 to 227 bytes for a classic 32 byte windows egghunter), but I wanted to illustrate how larger payloads lead to signifigantly shorter final shellcode.

Note: This was achieved without use of -o. -o produces much shorter shellcode.

- encoder.py

![Original](ASCII8.PNG)

- opt_encoder.py

![Opt](ASCII7.PNG)

- Dword example

![cases](ASCII9.PNG)

# Use Case
example.py, built with payloads generated by this encoder, uses encoded shellcode to exploit LTER in Vulnserver.

# Notes

Cool new features:
- The -o option for opt_encoder.py allows for extreme optimization by eliminating most badchars in favor of letting the user define their own. Use at your own risk, rather experimental. Doesn't have the "it just works" quality that both default encoders have, you'll likely have to run your own badchar analysis.
- Assembly will not print to terminal if output file specified.
- Shellcode generation! Done by hand but verified with ndisasm and works fine, I'm a bit frightened.
![shellcode](ASCII6.PNG)
- Eax normalizer now automatically adjusts to remove user-defined badchars.
![Normalizer](ASCII4.png)
- You can automatically set up the stack using the -e flag, takes the math out of stack setup.
![Stack setup](ASCII3.png)
- The program no longer allows the algorithm to give inaccurate results! This is not a very likely scenario, but it's possible there are just too many badchars for your particular payload to work.
![Program](ASCII5.png)

Shellcode length must be a multiple of 4 unless automatic padding is specified (-p). Nop padding can accomplish this. Shellcode must be in hex format.

- Used to exploit LTER in Vulnserver with shellcode containing null bytes (unencoded MSFVenom Reverse Shell).
- Confirmed working with most MSFVenom x86 encoders.

Known Compatibility Issues
- When used with MSFVenom Shikata_ga_nai encoder, has an unexplained tendency to overwrite the EIP. This may just be a debugger issue, as I have never encountered this problem using any other encoder or shellcode. - Not sure if this is still applicable, code has been rewritten.

Default (immutable) badchars: ```0x00,0x01-0x20 (includes 0x0d and 0x0a),0x3a,0x3f,0x40,0x2e,0x80-0xFF```

# Coming Soon
- ~~Optimize BUGTREE's algorith to use the minimum number of subtraction instructions~~ implemented as a second python file
- ~~Fix -n and -a conflict~~ fixed
- ~~Verbosity settings~~ implemented
- ~~Remove annoying extra byte that sometimes appears on verification sum~~ implemented
- ~~Automatic nop padding~~
implemented as an optional flag
- ~~Alignment of ESP by a user defined offset~~ implemented
- ~~Proper processing of "0x00000000" lines~~
implemented
- ~~Custom badchars, (currently badchars are 00, 20, 0a, 0d, 3a, 3f, and any character that's not printable, valid ASCII)~~
implemented
- ~~Custom output files for assembly code~~
implemented
- ~~Custom normalizer~~
implemented

# Coming Eventually
- ~~Automatic badchar-based normalizer adjustment~~ implemented
- ~~Production of shellcode in insertable format as an option~~ implemented as flag
- ~~Return byte length of generated shellcode~~ implemented
- Accept other shellcode formats as input
- ~~For opt_encoder.py - ability to remove all default badchars under 0x80 besides 0x0a, 0x0d, and 0x00. Use at your own risk.~~ implemented as optional flag.

