"""
Comprehensive tests for the generate_data_flow module.
Tests cover core data flow generation functions.
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import tempfile
from typing import Dict, List, Tuple

# Import the module under test
from src.generate_data_flow import (
    draw_focused_data_flow,
    draw_complete_data_flow,
    parse_dump
)

class TestGenerateDataFlow(unittest.TestCase):
    """Test the generate_data_flow functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.sample_nodes = {
            "table1": {
                "type": "table",
                "database": "db1",
                "full_name": "db1.table1",
                "definition": "CREATE TABLE table1"
            },
            "view1": {
                "type": "view", 
                "database": "db1",
                "full_name": "db1.view1",
                "definition": "CREATE VIEW view1 AS SELECT * FROM table1"
            }
        }
        
        self.sample_edges = [("table1", "view1")]

    @patch('src.generate_data_flow.pyvis_mod.draw_pyvis_html')
    def test_draw_complete_data_flow_basic(self, mock_draw_pyvis):
        """Test basic complete data flow generation."""
        mock_draw_pyvis.return_value = None
        
        # Test without auto-open
        result = draw_complete_data_flow(
            self.sample_edges,
            self.sample_nodes,
            save_path="/tmp/test",
            file_name="test_diagram",
            draw_edgeless=True,
            auto_open=False
        )
        
        # Verify pyvis draw function was called
        mock_draw_pyvis.assert_called_once_with(
            self.sample_edges,
            self.sample_nodes,
            save_path="/tmp/test",
            auto_open=False,
            file_name="test_diagram",
            draw_edgeless=True
        )
        self.assertIsNone(result)

    @patch('src.generate_data_flow.pyvis_mod.draw_pyvis_html')
    def test_draw_complete_data_flow_with_auto_open(self, mock_draw_pyvis):
        """Test complete data flow with auto-open."""
        mock_draw_pyvis.return_value = "/tmp/test/output.html"
        
        result = draw_complete_data_flow(
            self.sample_edges,
            self.sample_nodes,
            save_path="/tmp/test",
            file_name="test_diagram",
            draw_edgeless=True,
            auto_open=True
        )
        
        # Verify pyvis draw function was called with auto_open=True
        mock_draw_pyvis.assert_called_once_with(
            self.sample_edges,
            self.sample_nodes,
            save_path="/tmp/test",
            auto_open=True,
            file_name="test_diagram",
            draw_edgeless=True
        )
        self.assertEqual(result, "/tmp/test/output.html")

    @patch('src.generate_data_flow.pyvis_mod.draw_pyvis_html')
    @patch('src.generate_data_flow.nx.DiGraph')
    def test_draw_focused_data_flow_basic(self, mock_digraph, mock_draw_pyvis):
        """Test basic focused data flow generation."""
        # Mock NetworkX graph
        mock_graph = MagicMock()
        mock_digraph.return_value = mock_graph
        
        # Set up the graph to contain the focus nodes
        mock_graph.__contains__ = MagicMock(side_effect=lambda x: x in ["table1", "view1"])
        mock_graph.nodes.return_value = ["table1"]
        mock_graph.edges.return_value = [("table1", "view1")]
        
        # Mock subgraph operations
        mock_subgraph = MagicMock()
        mock_subgraph.nodes.return_value = ["table1"]
        mock_subgraph.edges.return_value = [("table1", "view1")]
        mock_graph.subgraph.return_value.copy.return_value = mock_subgraph
        
        # Mock NetworkX functions
        with patch('src.generate_data_flow.nx.ancestors', return_value=set()), \
             patch('src.generate_data_flow.nx.descendants', return_value=set()):
            
            mock_draw_pyvis.return_value = None
            
            result = draw_focused_data_flow(
                self.sample_edges,
                self.sample_nodes,
                focus_nodes=["table1"],
                save_path="/tmp/test",
                file_name="test_focused",
                see_ancestors=True,
                see_descendants=True,
                auto_open=False
            )
            
            # Verify graph operations
            mock_graph.add_edges_from.assert_called_with(self.sample_edges)
            mock_draw_pyvis.assert_called_once()

    @patch('src.generate_data_flow.pyvis_mod.draw_pyvis_html')
    @patch('src.generate_data_flow.nx.DiGraph')
    def test_draw_focused_data_flow_empty_focus_nodes(self, mock_digraph, mock_draw_pyvis):
        """Test focused data flow with empty focus nodes."""
        mock_graph = MagicMock()
        mock_digraph.return_value = mock_graph
        mock_graph.__contains__ = MagicMock(return_value=False)  # No nodes found
        
        result = draw_focused_data_flow(
            self.sample_edges,
            self.sample_nodes,
            focus_nodes=[],
            save_path="/tmp/test",
            file_name="test_empty",
            see_ancestors=True,
            see_descendants=True,
            auto_open=False
        )
        
        # Should return None for empty focus nodes
        self.assertIsNone(result)
        mock_draw_pyvis.assert_not_called()

    @patch('src.generate_data_flow.pyvis_mod.draw_pyvis_html')
    def test_draw_complete_data_flow_no_edgeless(self, mock_draw_pyvis):
        """Test complete data flow without drawing edgeless nodes."""
        mock_draw_pyvis.return_value = None
        
        draw_complete_data_flow(
            self.sample_edges,
            self.sample_nodes,
            save_path="/tmp/test",
            file_name="test_diagram",
            draw_edgeless=False,
            auto_open=False
        )
        
        # Verify draw_edgeless=False was passed
        mock_draw_pyvis.assert_called_once_with(
            self.sample_edges,
            self.sample_nodes,
            save_path="/tmp/test",
            auto_open=False,
            file_name="test_diagram",
            draw_edgeless=False
        )

    @patch('src.generate_data_flow.guess_database_type')
    @patch('src.generate_data_flow._PARSER_REGISTRY')
    def test_parse_dump_delegates_to_parser(self, mock_registry, mock_guess_db_type):
        """Test that parse_dump delegates to the appropriate parser."""
        # Mock database type detection
        mock_guess_db_type.return_value = "denodo"
        
        # Mock parser
        mock_parser = MagicMock()
        mock_parser.parse_dump.return_value = ([], {}, {})
        mock_registry.__contains__ = MagicMock(return_value=True)
        mock_registry.__getitem__ = MagicMock(return_value=mock_parser)
        
        result = parse_dump("/fake/path/test.sql")
        
        mock_guess_db_type.assert_called_once_with("/fake/path/test.sql")
        mock_parser.parse_dump.assert_called_once_with("/fake/path/test.sql")
        self.assertEqual(result, ([], {}, {}))

    @patch('src.generate_data_flow.guess_database_type')
    @patch('src.generate_data_flow._PARSER_REGISTRY')
    def test_parse_dump_with_explicit_database_type(self, mock_registry, mock_guess_db_type):
        """Test parse_dump with explicit database type."""
        # Mock parser
        mock_parser = MagicMock()
        mock_parser.parse_dump.return_value = (
            [("table1", "view1")],
            {"table1": {"type": "table"}, "view1": {"type": "view"}},
            {"db1": 2}
        )
        mock_registry.__contains__ = MagicMock(return_value=True)
        mock_registry.__getitem__ = MagicMock(return_value=mock_parser)
        
        from src.parser_register import DatabaseType
        result = parse_dump("/fake/path/test.sql", database_type=DatabaseType.POSTGRESQL)
        
        # Should not call guess_database_type when explicit type provided
        mock_guess_db_type.assert_not_called()
        mock_parser.parse_dump.assert_called_once_with("/fake/path/test.sql")
        
        edges, nodes, stats = result
        self.assertEqual(len(edges), 1)
        self.assertEqual(len(nodes), 2)
        self.assertEqual(stats["db1"], 2)

    def test_parse_dump_unsupported_database_type(self):
        """Test parse_dump with unsupported database type."""
        with patch('src.generate_data_flow.guess_database_type', return_value="unsupported"), \
             patch('src.generate_data_flow._PARSER_REGISTRY', {}):
            
            with self.assertRaises(ValueError) as context:
                parse_dump("/fake/path/test.sql")
            
            self.assertIn("Unsupported or unrecognized database type", str(context.exception))

if __name__ == "__main__":
    unittest.main()
