import re
import glob
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

chat_file = glob.glob('d:\\mipanel\\MaximusVpsMx\\chat_export\\*.txt')[0]

hwid_pattern = re.compile(r'\b[A-Fa-f0-9]{32}\b|\b[A-Fa-f0-9]{16}\b')

results = {}
with open(chat_file, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        parts = line.split(' - ', 1)
        if len(parts) > 1:
            msg_part = parts[1]
            if ': ' in msg_part:
                sender, msg = msg_part.split(': ', 1)
                sender = sender.strip()
                # Clean up sender name (remove non-ascii for alias if necessary, but utf-8 is fine for now)
                matches = hwid_pattern.findall(msg)
                for match in matches:
                    if not match.isdigit():
                        results[sender] = match

with open('d:\\mipanel\\MaximusVpsMx\\extracted_hwids.txt', 'w', encoding='utf-8') as f:
    for sender, hwid in results.items():
        f.write(f"{sender}|{hwid}\n")

print(f"Total unique HWIDs found: {len(results)}")
