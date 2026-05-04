import os
import json
import requests
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv("/app/.env", override=True)

MITRE_ATTACK_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

CWE_TO_TECHNIQUE = {
    'CWE-79': {'id': 'T1189', 'name': 'Drive-by Compromise', 'tactic': 'initial-access'},
    'CWE-89': {'id': 'T1190', 'name': 'Exploit Public-Facing Application', 'tactic': 'initial-access'},
    'CWE-78': {'id': 'T1059', 'name': 'Command and Scripting Interpreter', 'tactic': 'execution'},
    'CWE-94': {'id': 'T1059', 'name': 'Command and Scripting Interpreter', 'tactic': 'execution'},
    'CWE-22': {'id': 'T1083', 'name': 'File and Directory Discovery', 'tactic': 'discovery'},
    'CWE-287': {'id': 'T1078', 'name': 'Valid Accounts', 'tactic': 'persistence'},
    'CWE-269': {'id': 'T1078', 'name': 'Valid Accounts', 'tactic': 'privilege-escalation'},
    'CWE-119': {'id': 'T1203', 'name': 'Exploitation for Client Execution', 'tactic': 'execution'},
    'CWE-352': {'id': 'T1204', 'name': 'User Execution', 'tactic': 'execution'},
    'CWE-434': {'id': 'T1190', 'name': 'Exploit Public-Facing Application', 'tactic': 'initial-access'},
    'CWE-502': {'id': 'T1190', 'name': 'Exploit Public-Facing Application', 'tactic': 'initial-access'},
    'CWE-611': {'id': 'T1190', 'name': 'Exploit Public-Facing Application', 'tactic': 'initial-access'},
    'CWE-918': {'id': 'T1190', 'name': 'Exploit Public-Facing Application', 'tactic': 'initial-access'},
    'CWE-200': {'id': 'T1005', 'name': 'Data from Local System', 'tactic': 'collection'},
    'CWE-20': {'id': 'T1190', 'name': 'Exploit Public-Facing Application', 'tactic': 'initial-access'},
}


def get_attck_mapping(cwe_ids: list) -> list:
    mappings = []
    seen = set()
    for cwe in cwe_ids:
        technique = CWE_TO_TECHNIQUE.get(cwe)
        if technique and technique['id'] not in seen:
            mappings.append({**technique, 'source_cwe': cwe})
            seen.add(technique['id'])
    return mappings


def add_attck_to_kg(cve_id: str, cwe_ids: list):
    try:
        from kg_manager import get_kg_instance
        kg = get_kg_instance()
        if kg.driver is None:
            return

        mappings = get_attck_mapping(cwe_ids)
        with kg.driver.session() as session:
            for m in mappings:
                session.run("""
                    MERGE (t:ATTCKTechnique {id: $tech_id})
                    SET t.name = $name, t.tactic = $tactic
                    WITH t
                    MATCH (c:CVE {id: $cve_id})
                    MERGE (c)-[:MAPPED_TO]->(t)
                """, tech_id=m['id'], name=m['name'], tactic=m['tactic'], cve_id=cve_id)
    except Exception as e:
        print(f"ATT&CK mapping error for {cve_id}: {e}")


def get_epss_score(cve_id: str) -> dict:
    try:
        url = f"https://api.first.org/data/v1/epss?cve={cve_id}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get('data'):
                entry = data['data'][0]
                return {
                    'cve_id': cve_id,
                    'epss_score': float(entry.get('epss', 0)),
                    'percentile': float(entry.get('percentile', 0)),
                }
    except Exception as e:
        print(f"EPSS error for {cve_id}: {e}")
    return {'cve_id': cve_id, 'epss_score': 0.0, 'percentile': 0.0}


def generate_sbom(directory: str = "/workspace") -> dict:
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "components": [],
        "generated": datetime.now().isoformat()
    }

    requirements_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv', '__pycache__'}]
        for f in files:
            if f in ('requirements.txt', 'package.json', 'Pipfile', 'pyproject.toml'):
                requirements_files.append(os.path.join(root, f))

    for req_file in requirements_files:
        if req_file.endswith('requirements.txt'):
            with open(req_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        match = re.match(r'^([a-zA-Z0-9_-]+)\s*([>=<~!]=?\s*[\d.]+)?', line)
                        if match:
                            sbom["components"].append({
                                "type": "library",
                                "name": match.group(1),
                                "version": (match.group(2) or "").strip("=<>!~ "),
                                "purl": f"pkg:pypi/{match.group(1).lower()}"
                            })

    return sbom


def scan_secrets(directory: str = "/workspace") -> list:
    SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})', 'API Key'),
        (r'(?i)(secret|password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{8,})', 'Password/Secret'),
        (r'(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})', 'Bearer Token'),
        (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', 'Private Key'),
        (r'(?i)(aws_access_key_id|aws_secret_access_key)\s*[:=]\s*["\']?([a-zA-Z0-9/+=]{20,})', 'AWS Key'),
        (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Access Token'),
        (r'sk-[a-zA-Z0-9]{48}', 'OpenAI API Key'),
        (r'xoxb-[a-zA-Z0-9\-]+', 'Slack Bot Token'),
    ]

    findings = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', 'venv', '__pycache__', '.env'}]
        for fname in files:
            if fname.endswith(('.py', '.js', '.ts', '.json', '.yaml', '.yml', '.toml', '.cfg', '.ini', '.conf')):
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            for pattern, secret_type in SECRET_PATTERNS:
                                if re.search(pattern, line):
                                    findings.append({
                                        'file': fpath,
                                        'line': line_num,
                                        'type': secret_type,
                                        'snippet': line.strip()[:100]
                                    })
                except Exception:
                    pass

    return findings


def enrich_cve_with_epss(cve_id: str, details: dict) -> dict:
    epss = get_epss_score(cve_id)
    details['epss_score'] = epss['epss_score']
    details['epss_percentile'] = epss['percentile']

    cwe_ids = details.get('cwe_ids', [])
    if cwe_ids:
        add_attck_to_kg(cve_id, cwe_ids)
        attck = get_attck_mapping(cwe_ids)
        details['mitre_attack'] = attck

    return details


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "sbom":
            sbom = generate_sbom(sys.argv[2] if len(sys.argv) > 2 else "/workspace")
            print(json.dumps(sbom, indent=2))
        elif cmd == "secrets":
            findings = scan_secrets(sys.argv[2] if len(sys.argv) > 2 else "/workspace")
            print(f"Found {len(findings)} potential secrets")
            for f in findings[:10]:
                print(f"  {f['file']}:{f['line']} - {f['type']}")
        elif cmd == "epss":
            cve_id = sys.argv[2]
            print(json.dumps(get_epss_score(cve_id), indent=2))
        elif cmd == "attck":
            cwe_ids = sys.argv[2:]
            mappings = get_attck_mapping(cwe_ids)
            print(json.dumps(mappings, indent=2))
