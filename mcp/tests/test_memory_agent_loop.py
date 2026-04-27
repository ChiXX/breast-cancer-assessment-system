import unittest
from unittest.mock import MagicMock, patch
from mcp.agents.memory_agent import MemoryAgent

class TestMemoryAgent(unittest.TestCase):
    def setUp(self):
        # Patch dashscope and environment variables
        with patch.dict('os.environ', {'DASHSCOPE_API_KEY': 'fake_key'}):
            self.agent = MemoryAgent()

    @patch('mcp.agents.tools.memory_tools.CreateMemory.call')
    def test_process_session_no_loop(self, mock_create_memory):
        # Mock the LLM to return a valid JSON summary
        mock_response = {'content': '{"title": "Test Title", "summary": "Test Summary"}'}
        self.agent.agent.llm.chat = MagicMock(return_value=[mock_response])
        mock_create_memory.return_value = {'status': 'success', 'path': '/tmp/test.json'}

        history = [
            {'role': 'user', 'content': 'I have a headache.'},
            {'role': 'assistant', 'content': 'Sorry to hear that.'}
        ]
        
        # This should call llm.chat once and NOT loop
        result = self.agent.process_session("test_session", history)
        
        self.assertIn("记忆已归档", result)
        self.agent.agent.llm.chat.assert_called_once()
        mock_create_memory.assert_called_once()

if __name__ == "__main__":
    unittest.main()
