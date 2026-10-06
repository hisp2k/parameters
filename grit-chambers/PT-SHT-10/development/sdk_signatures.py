from pathlib import Path
b=Path(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\API\flow simulation api sdk x64.exe').read_bytes()
for x in [bytes.fromhex('377abcaf271c'),bytes.fromhex('504b0304'),b'MSCF',b'Inno Setup',b'Nullsoft']:
 print(x,b.find(x),b.rfind(x))
