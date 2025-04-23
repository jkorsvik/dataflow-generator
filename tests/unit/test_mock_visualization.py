import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import networkx as nx
from src.generate_data_flow import draw_complete_data_flow, draw_focused_data_flow

class TestVisualization(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.edges = [
            ("table1", "view1"),
            ("table2", "view1"),
            ("view1", "view2")
        ]
        self.node_types = {
            "table1": {"type": "table", "database": "db1", "full_name": "db1.table1"},
            "table2": {"type": "table", "database": "db2", "full_name": "db2.table2"},
            "view1": {"type": "view", "database": "db3", "full_name": "db3.view1"},
            "view2": {"type": "view", "database": "db3", "full_name": "db3.view2"}
        }
        self.test_dir = "test_output"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)

    @patch('src.pyvis_mod.Network')
    @patch('builtins.open', new_callable=mock_open)
    def test_complete_data_flow_generation(self, mock_file, mock_network):
        """Test complete data flow visualization generation"""
        # Mock the Network instance
        mock_network_instance = MagicMock()
        mock_network.return_value = mock_network_instance
        
        # Call the function
        draw_complete_data_flow(
            self.edges,
            self.node_types,
            save_path=self.test_dir,
            file_name="test_flow"
        )
        
        # Verify that the Network was created
        mock_network.assert_called_once()
        
        # Verify nodes and edges were added
        self.assertGreater(mock_network_instance.add_node.call_count, 0)
        self.assertGreater(mock_network_instance.add_edge.call_count, 0)
        
        # Verify files were created
        expected_path = os.path.join(self.test_dir, "data_flow_pyvis_test_flow.html")
        mock_file.assert_called_with(expected_path, 'w', encoding='utf-8')

    @patch('src.pyvis_mod.Network')
    @patch('builtins.open', new_callable=mock_open)
    def test_focused_data_flow_generation(self, mock_file, mock_network):
        """Test focused data flow visualization generation"""
        mock_network_instance = MagicMock()
        mock_network.return_value = mock_network_instance
        
        focus_nodes = ["view1"]
        
        # Call the function
        draw_focused_data_flow(
            self.edges,
            self.node_types,
            focus_nodes,
            save_path=self.test_dir,
            file_name="test_focused"
        )
        
        # Verify that the Network was created with focused configuration
        mock_network.assert_called_once()
        
        # Verify files were created
        expected_path = os.path.join(self.test_dir, "focused_data_flow_test_focused.html")
        mock_file.assert_called_with(expected_path, 'w', encoding='utf-8')

    @patch('src.pyvis_mod.Network')
    def test_node_styling(self, mock_network):
        """Test that nodes are styled correctly based on type"""
        mock_network_instance = MagicMock()
        mock_network.return_value = mock_network_instance
        
        draw_complete_data_flow(
            self.edges,
            self.node_types,
            save_path=self.test_dir
        )
        
        # Check that different node types got different styling
        node_calls = mock_network_instance.add_node.call_args_list
        
        table_styles = [call for call in node_calls 
                       if call.args[0] in ['table1', 'table2']]
        view_styles = [call for call in node_calls 
                      if call.args[0] in ['view1', 'view2']]
        
        # Verify tables and views got different colors/styles
        self.assertNotEqual(
            table_styles[0].kwargs.get('color'),
            view_styles[0].kwargs.get('color')
        )

    @patch('src.pyvis_mod.Network')
    def test_edge_direction(self, mock_network):
        """Test that edges maintain correct direction in visualization"""
        mock_network_instance = MagicMock()
        mock_network.return_value = mock_network_instance
        
        draw_complete_data_flow(
            self.edges,
            self.node_types,
            save_path=self.test_dir
        )
        
        edge_calls = mock_network_instance.add_edge.call_args_list
        
        # Verify that edges maintain source -> target direction
        edge_directions = [(call.args[0], call.args[1]) for call in edge_calls]
        self.assertIn(("table1", "view1"), edge_directions)
        self.assertIn(("table2", "view1"), edge_directions)
        self.assertIn(("view1", "view2"), edge_directions)

    def test_invalid_focus_nodes(self):
        """Test handling of invalid focus nodes"""
        # NO LOGGING YET
        # with self.assertLogs(level='WARNING'):
        #     draw_focused_data_flow(
        #         self.edges,
        #         self.node_types,
        #         focus_nodes=["nonexistent_node"],
        #         save_path=self.test_dir
        #     )
        pass

    def tearDown(self):
        """Clean up test directory"""
        if os.path.exists(self.test_dir):
            # Only remove files we created, not the directory itself
            for file in os.listdir(self.test_dir):
                if file.startswith(("data_flow_", "focused_data_flow_")):
                    os.remove(os.path.join(self.test_dir, file))

if __name__ == '__main__':
    unittest.main()
