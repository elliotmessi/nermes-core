#!/usr/bin/env python3
"""Fix Hermes brand references in merged upstream code."""
import sys

TARGET = sys.argv[1] if len(sys.argv) > 1 else '/home/elliot/projects/nermes-core/hermes_cli/main.py'

with open(TARGET, 'r') as f:
    content = f.read()

# Only replace user-facing strings, not code identifiers
reps = [
    ('看起来 Hermes 尚未配置', '看起来 Nermes 尚未配置'),
    ('您将如何使用 WhatsApp 与 Hermes？', '您将如何使用 WhatsApp 与 Nermes？'),
    ('\u2695 Hermes Agent', '\u2695 Nermes'),
    ('Use Hermes URL heuristics', 'Use Nermes URL heuristics'),
    ('模型。Hermes 将探测', '模型。Nermes 将探测'),
    ('delegates Hermes turns', 'delegates Nermes turns'),
    ('Hermes currently starts its own ACP', 'Nermes currently starts its own ACP'),
    ('Hermes typically makes 3-10', 'Nermes typically makes 3-10'),
    ('To use Gemini with Hermes', 'To use Gemini with Nermes'),
    ('afterward if Hermes behaves', 'afterward if Nermes behaves'),
    ("Hermes couldn't find", "Nermes couldn't find"),
    ("Hermes couldn't drop", "Nermes couldn't drop"),
    ('Hermes behaves unexpectedly', 'Nermes behaves unexpectedly'),
    ('the official Hermes repository', 'the official Hermes repository (upstream)'),
    ('Close Hermes Desktop', 'Close Nermes Desktop'),
    ('Hermes Desktop backend', 'Nermes Desktop backend'),
    ('Hermes Desktop / gateway', 'Nermes Desktop / gateway'),
    ('update Hermes Agent', 'update Nermes'),
    ('Update Hermes via pip', 'Update Nermes via pip'),
    ('Legacy Hermes gateway', 'Legacy Nermes gateway'),
    ('Requires:     Hermes', 'Requires:     Nermes'),
    ('Requires: Hermes', 'Requires: Nermes'),
    ('View and filter Hermes log', 'View and filter Nermes log'),
    ('helpers for Hermes', 'helpers for Nermes'),
    ('flow for Hermes CLI', 'flow for Nermes CLI'),
    ('Authenticate Hermes with', 'Authenticate Nermes with'),
    ('summary of your Hermes setup', 'summary of your Nermes setup'),
    ('entire Hermes configuration', 'entire Nermes configuration'),
    ('Hermes backup', 'Nermes backup'),
    ('run Hermes as an MCP', 'run Nermes as an MCP'),
    ('expose Hermes conversations', 'expose Nermes conversations'),
    ('Run Hermes as an MCP', 'Run Nermes as an MCP'),
    ('OpenClaw to Hermes', 'OpenClaw to Nermes'),
    ('Print Hermes ACP', 'Print Nermes ACP'),
    ('interactive Hermes provider', 'interactive Nermes provider'),
    ('Install a Hermes profile', 'Install a Nermes profile'),
]

count = 0
for old, new in reps:
    n = content.count(old)
    if n > 0:
        content = content.replace(old, new)
        count += n

with open(TARGET, 'w') as f:
    f.write(content)

print(f'Fixed {count} occurrences in {TARGET}')
