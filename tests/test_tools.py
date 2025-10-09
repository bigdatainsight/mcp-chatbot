import json
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
import pytest
from mcp_chatbot.tools import search_papers, extract_info, execute_tool


@pytest.fixture
def temp_paper_dir(monkeypatch):
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        paper_dir = os.path.join(temp_dir, "papers")
        monkeypatch.setattr("mcp_chatbot.tools.PAPER_DIR", paper_dir)
        yield paper_dir


@pytest.fixture
def mock_arxiv_paper():
    """Mock arxiv paper object."""
    paper = Mock()
    paper.get_short_id.return_value = "1234.5678"
    paper.title = "Test Paper"
    # Create proper mock authors with name attribute
    author1 = Mock()
    author1.name = "John Doe"
    author2 = Mock()
    author2.name = "Jane Smith"
    paper.authors = [author1, author2]
    paper.summary = "Test summary"
    paper.pdf_url = "http://test.pdf"
    paper.published.date.return_value = "2023-01-01"
    return paper


class TestSearchPapers:
    @patch("mcp_chatbot.tools.arxiv.Client")
    def test_search_papers_success(self, mock_client, temp_paper_dir, mock_arxiv_paper):
        """Test successful paper search."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.results.return_value = [mock_arxiv_paper]
        
        result = search_papers("test topic", max_results=1)
        
        assert result == ["1234.5678"]
        assert os.path.exists(os.path.join(temp_paper_dir, "test_topic", "papers_info.json"))

    @patch("mcp_chatbot.tools.arxiv.Client")
    def test_search_papers_empty_results(self, mock_client, temp_paper_dir):
        """Test search with no results."""
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.results.return_value = []
        
        result = search_papers("nonexistent topic")
        
        assert result == []


class TestExtractInfo:
    def test_extract_info_found(self, temp_paper_dir):
        """Test extracting existing paper info."""
        # Setup test data
        topic_dir = os.path.join(temp_paper_dir, "test_topic")
        os.makedirs(topic_dir, exist_ok=True)
        
        paper_data = {
            "1234.5678": {
                "title": "Test Paper",
                "authors": ["John Doe"],
                "summary": "Test summary"
            }
        }
        
        with open(os.path.join(topic_dir, "papers_info.json"), "w") as f:
            json.dump(paper_data, f)
        
        result = extract_info("1234.5678")
        
        assert "Test Paper" in result
        assert "John Doe" in result

    def test_extract_info_not_found(self, temp_paper_dir):
        """Test extracting non-existent paper info."""
        # Create the paper directory but no files
        os.makedirs(temp_paper_dir, exist_ok=True)
        
        result = extract_info("nonexistent.paper")
        
        assert "There's no saved information related to paper nonexistent.paper" in result

    def test_extract_info_no_paper_dir(self, monkeypatch):
        """Test when paper directory doesn't exist."""
        monkeypatch.setattr("mcp_chatbot.tools.PAPER_DIR", "/nonexistent/path")
        
        with pytest.raises(FileNotFoundError):
            extract_info("1234.5678")


class TestExecuteTool:
    def test_execute_tool_search_papers(self):
        """Test executing search_papers tool."""
        mock_search = Mock(return_value=["1234.5678", "9876.5432"])
        
        with patch("mcp_chatbot.tools.mapping_tool_function", {"search_papers": mock_search}):
            result = execute_tool("search_papers", {"topic": "test", "max_results": 2})
            
            assert result == "1234.5678, 9876.5432"
            mock_search.assert_called_once_with(topic="test", max_results=2)

    def test_execute_tool_extract_info(self):
        """Test executing extract_info tool."""
        mock_extract = Mock(return_value='{"title": "Test Paper"}')
        
        with patch("mcp_chatbot.tools.mapping_tool_function", {"extract_info": mock_extract}):
            result = execute_tool("extract_info", {"paper_id": "1234.5678"})
            
            assert result == '{"title": "Test Paper"}'
            mock_extract.assert_called_once_with(paper_id="1234.5678")

    def test_execute_tool_none_result(self):
        """Test tool returning None."""
        with patch("mcp_chatbot.tools.mapping_tool_function", {"test_tool": lambda: None}):
            result = execute_tool("test_tool", {})
            assert result == "The operation completed but didn't return any results."

    def test_execute_tool_dict_result(self):
        """Test tool returning dictionary."""
        test_dict = {"key": "value"}
        with patch("mcp_chatbot.tools.mapping_tool_function", {"test_tool": lambda: test_dict}):
            result = execute_tool("test_tool", {})
            assert '"key": "value"' in result