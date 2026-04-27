import os
import shutil
import pytest
import yaml
from mcp.agents.tools.skill_tools import ReadSkill, UpsertSkill, UpsertSkillResource, ResolveSkillReferences

TEST_SKILL_DIR = os.path.abspath("mcp/agents/skills/test-skill")

@pytest.fixture
def clean_test_skill():
    if os.path.exists(TEST_SKILL_DIR):
        shutil.rmtree(TEST_SKILL_DIR)
    yield
    if os.path.exists(TEST_SKILL_DIR):
        shutil.rmtree(TEST_SKILL_DIR)

def test_upsert_and_read_skill_md(clean_test_skill):
    upsert = UpsertSkill()
    skill_name = "test-skill"
    description = "A test skill for SKILL.md"
    content = "## Test Content\nThis is a test."
    
    # Test Upsert
    res = upsert.call({
        'skill_name': skill_name,
        'description': description,
        'content': content
    })
    
    assert res['status'] == 'success'
    skill_md_path = os.path.join(TEST_SKILL_DIR, 'SKILL.md')
    assert os.path.exists(skill_md_path)
    
    with open(skill_md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
        assert md_content.startswith('---')
        assert f"name: {skill_name}" in md_content
        assert f"description: {description}" in md_content
        assert content in md_content

    # Test Read
    read = ReadSkill()
    res = read.call({'skill_name': skill_name})
    assert res['status'] == 'success'
    assert res['name'] == skill_name
    assert res['metadata']['description'] == description
    assert content in res['content']

def test_upsert_and_resolve_resource_md(clean_test_skill):
    # Ensure skill dir exists
    os.makedirs(TEST_SKILL_DIR, exist_ok=True)
    
    upsert_res = UpsertSkillResource()
    resource_name = "sub-logic.md"
    content = '{"logic": "test"}'
    
    res = upsert_res.call({
        'skill_name': 'test-skill',
        'resource_name': resource_name,
        'content': content
    })
    
    assert res['status'] == 'success'
    resource_path = os.path.join(TEST_SKILL_DIR, 'sub-logic.md')
    assert os.path.exists(resource_path)
    
    # Test Resolve
    resolve = ResolveSkillReferences()
    res = resolve.call({
        'skill_name': 'test-skill',
        'resource_path': './sub-logic.md'
    })
    
    assert res['status'] == 'success'
    assert res['content'] == content
