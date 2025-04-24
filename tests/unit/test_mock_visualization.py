import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock
import networkx as nx
from src.generate_data_flow import draw_complete_data_flow, draw_focused_data_flow


class TestMockGraphVisualization(unittest.TestCase):
    """Test visualization functionality with mocked components"""

    def setUp(self):
        """Create test data for graph visualization"""
        self.test_dir = tempfile.mkdtemp()
        # Define edges for test dataflow
        self.edges = [
            ("table1", "view1"),
            ("table2", "view1"),
            ("view1", "view2"),
        ]
        # Define node types dictionary with required format
        self.node_types = {
            "table1": {"type": "table", "database": "db1", "full_name": "table1"},
            "table2": {"type": "table", "database": "db1", "full_name": "table2"},
            "view1": {"type": "view", "database": "db1", "full_name": "view1"},
            "view2": {"type": "view", "database": "db1", "full_name": "view2"},
        }

    @patch("src.pyvis_mod.draw_pyvis_html")
    def test_complete_data_flow_generation(self, mock_draw_pyvis):
        """Test complete data flow visualization generation"""
        # Set up the return value for draw_pyvis_html
        mock_draw_pyvis.return_value = None

        # Call function under test
        draw_complete_data_flow(
            self.edges,
            self.node_types,
            save_path=self.test_dir,
            file_name="test_complete",
            auto_open=False,
        )

        # Verify draw_pyvis_html was called with correct parameters
        mock_draw_pyvis.assert_called_once()
        call_args = mock_draw_pyvis.call_args[0]
        call_kwargs = mock_draw_pyvis.call_args[1]

        # Check first two positional args (edges and node_types)
        self.assertEqual(call_args[0], self.edges)
        self.assertEqual(call_args[1], self.node_types)

        # Check keyword args
        self.assertEqual(call_kwargs["save_path"], self.test_dir)
        self.assertEqual(call_kwargs["file_name"], "test_complete")
        self.assertEqual(call_kwargs["auto_open"], False)

    @patch("src.pyvis_mod.draw_pyvis_html")
    def test_focused_data_flow_generation(self, mock_draw_pyvis):
        """Test focused data flow visualization generation by checking that NetworkX is used to find ancestors and descendants"""
        # Set up the return value for draw_pyvis_html
        mock_draw_pyvis.return_value = None

        # Create actual edges and focus nodes to match the implementation
        edges = self.edges
        node_types = self.node_types
        focus_nodes = ["view1"]
        save_path = self.test_dir
        file_name = "test_focused"
        auto_open = False

        # Create a real directed graph for mocked functions to operate on
        mock_graph = MagicMock()

        # Create a patched version of nx.DiGraph that returns our mock_graph
        with patch("networkx.DiGraph", return_value=mock_graph) as mock_digraph:
            # Mock the check for 'node in G' to return True for our focus node
            mock_graph.__contains__.return_value = True

            # Create patches for nx.ancestors and nx.descendants
            with patch("networkx.ancestors") as mock_ancestors:
                with patch("networkx.descendants") as mock_descendants:
                    # Set return values for our mocked functions
                    mock_ancestors.return_value = {"table1", "table2"}
                    mock_descendants.return_value = {"view2"}

                    # Mock the subgraph and copy methods
                    mock_subgraph = MagicMock()
                    mock_graph.subgraph.return_value = mock_subgraph
                    mock_copy = MagicMock()
                    mock_subgraph.copy.return_value = mock_copy
                    mock_copy.nodes.return_value = [
                        "table1",
                        "table2",
                        "view1",
                        "view2",
                    ]
                    mock_copy.edges.return_value = self.edges

                    # Call function under test
                    draw_focused_data_flow(
                        edges,
                        node_types,
                        focus_nodes=focus_nodes,
                        save_path=save_path,
                        file_name=file_name,
                        auto_open=auto_open,
                    )

                    # Verify DiGraph was created
                    mock_digraph.assert_called_once()

                    # Verify edges were added to the graph
                    mock_graph.add_edges_from.assert_called_once_with(edges)

                    # Verify ancestors and descendants were called with the focus node
                    mock_ancestors.assert_called_once_with(mock_graph, "view1")
                    mock_descendants.assert_called_once_with(mock_graph, "view1")

                    # Verify the subgraph was created and copied
                    mock_graph.subgraph.assert_called_once()
                    mock_subgraph.copy.assert_called_once()

                    # Verify draw_pyvis_html was called with the focused subgraph
                    mock_draw_pyvis.assert_called_once()

    @patch("src.pyvis_mod.draw_pyvis_html")
    def test_node_styling(self, mock_draw_pyvis):
        """Test that nodes are styled according to their type"""
        # Call function under test
        draw_complete_data_flow(
            self.edges,
            self.node_types,
            save_path=self.test_dir,
            file_name="test_styling",
            auto_open=False,
        )

        # Verify draw_pyvis_html was called with the correct node types
        mock_draw_pyvis.assert_called_once()
        _, node_types_arg = mock_draw_pyvis.call_args[0]
        self.assertEqual(node_types_arg, self.node_types)

    @patch("src.pyvis_mod.draw_pyvis_html")
    def test_edge_direction(self, mock_draw_pyvis):
        """Test that edges maintain the correct direction in the visualization"""
        # Call function under test
        draw_complete_data_flow(
            self.edges,
            self.node_types,
            save_path=self.test_dir,
            file_name="test_direction",
            auto_open=False,
        )

        # Verify draw_pyvis_html was called with edges in the correct direction
        mock_draw_pyvis.assert_called_once()
        edges_arg = mock_draw_pyvis.call_args[0][0]
        self.assertEqual(edges_arg, self.edges)

    @patch("src.pyvis_mod.draw_pyvis_html")
    def test_invalid_focus_nodes(self, mock_draw_pyvis):
        """Test behavior when focus nodes don't exist in the graph"""
        # Create a focus node that doesn't exist
        focus_nodes = ["nonexistent_node"]

        # Create a mock graph where the focus node doesn't exist
        with patch("networkx.DiGraph") as mock_digraph_class:
            mock_graph = MagicMock()
            mock_digraph_class.return_value = mock_graph

            # Mock the containment check to return False
            mock_graph.__contains__.return_value = False

            # Call the function under test
            draw_focused_data_flow(
                self.edges,
                self.node_types,
                focus_nodes=focus_nodes,
                save_path=self.test_dir,
                file_name="test_invalid_focus",
                auto_open=False,
            )

            # Verify that draw_pyvis_html was not called (function returns early)
            mock_draw_pyvis.assert_not_called()

    def tearDown(self):
        """Clean up test directory"""
        shutil.rmtree(self.test_dir)


if __name__ == "__main__":
    unittest.main()
