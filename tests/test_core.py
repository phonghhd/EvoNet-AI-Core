import pytest
import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestRegexBlacklistGuardrail:
    def test_safe_code_passes(self):
        from scripts.system_watchdog import regex_blacklist_guardrail
        assert regex_blacklist_guardrail("def hello():\n    print('world')") is True

    def test_os_remove_blocked(self):
        from scripts.system_watchdog import regex_blacklist_guardrail
        with pytest.raises(Exception, match="Blocked"):
            regex_blacklist_guardrail("os.remove('/tmp/file')")

    def test_rm_rf_blocked(self):
        from scripts.system_watchdog import regex_blacklist_guardrail
        with pytest.raises(Exception, match="Blocked"):
            regex_blacklist_guardrail("rm -rf /")

    def test_eval_blocked(self):
        from scripts.system_watchdog import regex_blacklist_guardrail
        with pytest.raises(Exception, match="Blocked"):
            regex_blacklist_guardrail("eval('code')")

    def test_drop_table_blocked(self):
        from scripts.system_watchdog import regex_blacklist_guardrail
        with pytest.raises(Exception, match="Blocked"):
            regex_blacklist_guardrail("DROP TABLE users;")

    def test_shutil_rmtree_blocked(self):
        from scripts.system_watchdog import regex_blacklist_guardrail
        with pytest.raises(Exception, match="Blocked"):
            regex_blacklist_guardrail("shutil.rmtree('/tmp')")


class TestMultiLanguageSupport:
    def test_detect_python(self):
        from scripts.multi_language_support import MultiLanguageSupport
        assert MultiLanguageSupport().detect_language("main.py") == "python"

    def test_detect_javascript(self):
        from scripts.multi_language_support import MultiLanguageSupport
        assert MultiLanguageSupport().detect_language("app.js") == "javascript"

    def test_detect_typescript(self):
        from scripts.multi_language_support import MultiLanguageSupport
        assert MultiLanguageSupport().detect_language("index.ts") == "typescript"

    def test_detect_unknown(self):
        from scripts.multi_language_support import MultiLanguageSupport
        assert MultiLanguageSupport().detect_language("file.xyz") is None

    def test_extract_functions(self):
        from scripts.multi_language_support import MultiLanguageSupport
        mls = MultiLanguageSupport()
        code = "def hello():\n    pass\ndef world():\n    pass"
        funcs = mls.extract_functions(code, "python")
        assert "hello" in funcs
        assert "world" in funcs

    def test_extract_classes(self):
        from scripts.multi_language_support import MultiLanguageSupport
        mls = MultiLanguageSupport()
        code = "class MyClass:\n    pass\nclass Another:\n    pass"
        classes = mls.extract_classes(code, "python")
        assert "MyClass" in classes

    def test_supported_languages(self):
        from scripts.multi_language_support import MultiLanguageSupport
        langs = MultiLanguageSupport().get_supported_languages()
        assert len(langs) >= 10
        assert "python" in langs


class TestAttackSimulator:
    def test_sql_payloads(self):
        from scripts.attack_simulator import AttackSimulator
        payloads = AttackSimulator().create_attack_payloads("sql_injection")
        assert len(payloads) > 0

    def test_xss_payloads(self):
        from scripts.attack_simulator import AttackSimulator
        payloads = AttackSimulator().create_attack_payloads("xss")
        assert len(payloads) > 0

    def test_report_pass(self):
        from scripts.attack_simulator import AttackSimulator
        sim = AttackSimulator()
        results = {"vulnerability_type": "sql_injection", "effectiveness": 85.0,
                   "total_attacks": 4, "protected_count": 3, "vulnerable_count": 1}
        report = sim.generate_attack_report(results)
        assert "85" in report

    def test_report_fail(self):
        from scripts.attack_simulator import AttackSimulator
        sim = AttackSimulator()
        results = {"vulnerability_type": "xss", "effectiveness": 30.0,
                   "total_attacks": 4, "protected_count": 1, "vulnerable_count": 3}
        report = sim.generate_attack_report(results)
        assert "FAIL" in report


class TestAnalyzeFeedback:
    def test_positive(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from main import analyze_user_feedback
        assert analyze_user_feedback("Câu trả lời rất tốt!", "") == "positive"

    def test_negative(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from main import analyze_user_feedback
        assert analyze_user_feedback("Trả lời sai rồi", "") == "negative"

    def test_neutral(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from main import analyze_user_feedback
        assert analyze_user_feedback("Cho tôi hỏi thêm", "") == "neutral"


class TestSimpleCache:
    def test_set_get(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from main import SimpleCache
        c = SimpleCache(max_size=10)
        c.set("key1", "value1")
        assert c.get("key1") == "value1"

    def test_miss(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from main import SimpleCache
        assert SimpleCache().get("nonexistent") is None

    def test_eviction(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from main import SimpleCache
        c = SimpleCache(max_size=2)
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        assert c.get("a") is None
        assert c.get("c") == 3


class TestSecurityGym:
    def test_env_creation(self):
        from rl_environment.security_gym import SecurityEnv
        env = SecurityEnv()
        assert env.action_space.n == 10
        assert env.observation_space.shape == (20,)

    def test_reset(self):
        from rl_environment.security_gym import SecurityEnv
        env = SecurityEnv()
        obs, info = env.reset()
        assert obs.shape == (20,)
        assert np.all(obs >= 0) and np.all(obs <= 1)

    def test_step(self):
        from rl_environment.security_gym import SecurityEnv
        env = SecurityEnv()
        env.reset()
        obs, reward, done, truncated, info = env.step(0)
        assert obs.shape == (20,)
        assert -1.0 <= reward <= 1.0

    def test_cve_reward_logic(self):
        from rl_environment.security_gym import SecurityEnv
        cve = {'id': 'TEST', 'cvss_score': 8.0, 'cwe_ids': ['CWE-79'],
               'exploit_maturity': 'high', 'affected_software': ['app']}
        env = SecurityEnv(cve_data=[cve])
        env.reset()
        _, r_xss, _, _, _ = env.step(1)  # Output encoding for XSS
        env.reset()
        _, r_other, _, _, _ = env.step(8)  # Training for XSS
        assert r_xss > r_other


class TestAdvancedSecurity:
    def test_attck_mapping(self):
        from scripts.advanced_security import get_attck_mapping
        mappings = get_attck_mapping(['CWE-89', 'CWE-79'])
        assert len(mappings) == 2
        assert any(m['id'] == 'T1190' for m in mappings)

    def test_attck_empty(self):
        from scripts.advanced_security import get_attck_mapping
        assert get_attck_mapping([]) == []

    def test_sbom_generation(self):
        from scripts.advanced_security import generate_sbom
        sbom = generate_sbom(os.path.dirname(__file__))
        assert sbom['bomFormat'] == 'CycloneDX'
        assert 'components' in sbom

    def test_secrets_scan_clean(self):
        from scripts.advanced_security import scan_secrets
        findings = scan_secrets(os.path.dirname(__file__))
        assert isinstance(findings, list)


class TestAnalyzePatch:
    def test_parse_ai_response(self):
        from scripts.analyze_patch import parse_ai_response
        response = """VULNERABILITY: SQL injection via user input
PATCH:
```python
def safe_query(user_input):
    sanitized = re.sub(r'[^a-zA-Z0-9]', '', user_input)
    return sanitized
```
MITIGATION:
- Use parameterized queries
- Validate all input
- Deploy WAF"""
        result = parse_ai_response(response)
        assert 'sql' in result['vulnerability'].lower() or 'SQL' in result['vulnerability']
        assert 'def safe_query' in result['patch_code']
        assert len(result['mitigation_steps']) == 3
