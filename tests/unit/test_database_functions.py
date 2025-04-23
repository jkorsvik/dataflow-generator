import unittest
from unittest.mock import patch, mock_open
from src.generate_data_flow import parse_vql, InvalidSQLError



class TestDatabaseFunctions(unittest.TestCase):
    def setUp(self):
        self.sample_vql = """
        CREATE OR REPLACE VIEW db1.test_view AS
        SELECT * FROM db2.test_table1
        JOIN db1.test_table2 ON test_table1.id = test_table2.id;

        CREATE OR REPLACE TABLE db3.test_table3 
        DATA_LOAD_QUERY = '
            SELECT * FROM db2.test_table4
            JOIN db1.test_table5 ON test_table4.id = test_table5.id;
        ';
        """

    @patch("builtins.open", new_callable=mock_open)
    def test_parse_vql_database_detection(self, mock_file):
        mock_file.return_value.__enter__.return_value.read.return_value = self.sample_vql
        edges, node_types, database_stats = parse_vql("dummy.vql")

        # Check database statistics
        self.assertEqual(database_stats["db1"], 3)  # test_view, test_table2, test_table5
        self.assertEqual(database_stats["db2"], 2)  # test_table1, test_table4
        self.assertEqual(database_stats["db3"], 1)  # test_table3

        # Check node type database information
        self.assertEqual(node_types["test_view"]["database"], "db1")
        self.assertEqual(node_types["test_table1"]["database"], "db2")
        self.assertEqual(node_types["test_table3"]["database"], "db3")

    @patch("builtins.open", new_callable=mock_open)
    def test_parse_vql_with_no_database_prefixes(self, mock_file):
        vql_content = """
        CREATE OR REPLACE VIEW test_view AS
        SELECT * FROM test_table;
        """
        mock_file.return_value.__enter__.return_value.read.return_value = vql_content
        edges, node_types, database_stats = parse_vql("dummy.vql")

        # Should have empty database fields when no prefixes present
        self.assertEqual(node_types["test_view"]["database"], "")
        self.assertEqual(node_types["test_table"]["database"], "")
        self.assertEqual(database_stats, {})

    @patch("builtins.open", new_callable=mock_open)
    def test_parse_vql_complex_queries(self, mock_file):
        vql_content = """
        CREATE OR REPLACE VIEW db1.complex_view AS
        WITH cte1 AS (
            SELECT * FROM db2.table1
            JOIN db3.table2 ON table1.id = table2.id
        ),
        cte2 AS (
            SELECT * FROM db1.table3
            WHERE EXISTS (SELECT 1 FROM db4.table4)
        )
        SELECT * FROM cte1 JOIN cte2 ON cte1.id = cte2.id;
        """
        mock_file.return_value.__enter__.return_value.read.return_value = vql_content
        edges, node_types, database_stats = parse_vql("dummy.vql")

        # Check database statistics (should be unchanged)
        self.assertEqual(database_stats["db1"], 2)
        self.assertEqual(database_stats["db2"], 1)
        self.assertEqual(database_stats["db3"], 1)
        self.assertEqual(database_stats["db4"], 1)

        # Assert node types (should be unchanged)
        self.assertEqual(node_types["complex_view"]["database"], "db1")
        self.assertEqual(node_types["complex_view"]["type"], "view")
        self.assertEqual(node_types["table1"]["database"], "db2")
        self.assertEqual(node_types["table1"]["type"], "table")
        # ... (rest of type assertions)

        # *** UPDATED Edge Assertions ***
        # Assert data flows through CTEs
        self.assertIn(("table1", "cte1"), edges)
        self.assertIn(("table2", "cte1"), edges)
        self.assertIn(("table3", "cte2"), edges)
        self.assertIn(("table4", "cte2"), edges) # Dependency from EXISTS subquery inside CTE
        self.assertIn(("cte1", "complex_view"), edges)
        self.assertIn(("cte2", "complex_view"), edges)

        # Assert direct edges from base tables to final view DO NOT exist (optional but good)
        self.assertNotIn(("table1", "complex_view"), edges)
        self.assertNotIn(("table2", "complex_view"), edges)
        self.assertNotIn(("table3", "complex_view"), edges)
        self.assertNotIn(("table4", "complex_view"), edges)

        # Assert CTE types
        self.assertEqual(node_types["cte1"]["type"], "cte_view")
        self.assertEqual(node_types["cte2"]["type"], "cte_view")

    @patch("builtins.open", new_callable=mock_open)
    def test_parse_vql_empty_file(self, mock_file):
        mock_file.return_value.__enter__.return_value.read.return_value = ""
        with self.assertRaises(InvalidSQLError):
            parse_vql("dummy.vql")


    @patch("builtins.open", new_callable=mock_open)
    def test_parse_vql_table_declaration_and_dependencies(self, mock_file):
        vql_content = r"""
        CREATE OR REPLACE TABLE iv_site_org_bax_pm I18N no (
            run_id:text (sourcetypeid = '12', sourcetypesize = '255'),
            year_month:text (sourcetypeid = '12', sourcetypesize = '255'),
            site_id:long (sourcetypeid = '-5', sourcetyperadix = '10', sourcetypesize = '19'),
            transaction_source:text (sourcetypeid = '12', sourcetypesize = '255'),
            merchant_id:text (sourcetypeid = '12', sourcetypesize = '255'),
            text_line3:text (sourcetypeid = '12', sourcetypesize = '255')
        )
        FOLDER = '/02_integration/transaction_segmentation'
        CACHE OFF
        TIMETOLIVEINCACHE DEFAULT
        ADD SEARCHMETHOD iv_site_org_bax_pm(
            I18N no
            CONSTRAINTS (
                 ADD run_id (any) OPT ANY
                 ADD year_month (any) OPT ANY
                 ADD site_id (any) OPT ANY
                 ADD transaction_source (any) OPT ANY
                 ADD merchant_id (any) OPT ANY
                 ADD text_line3 (any) OPT ANY
            )
            OUTPUTLIST (merchant_id, run_id, site_id, text_line3, year_month)
            WRAPPER (jdbc iv_site_org_bax_pm)
        )
        DATA_LOAD_QUERY = '
        SELECT
            ''dummy'' AS run_id,
            bs.year_month,
            bs.site_id,
            ''396'' AS transaction_source,
            mc.merchant_id_original AS merchant_id,
            mc.text_line3_original AS text_line3
        FROM i_bv_business_site_bax_pm AS bs
        RIGHT JOIN i_bv_merchants_bax_pm_corrected mc
            ON bs.merchant_id = mc.merchant_id_cleaned 
            AND bs.year_month = mc.year_month 
            AND bs.text_line3 = mc.text_line3_original
        LEFT JOIN (
            SELECT
                organisasjonsnummer,
                navn AS org_name
            FROM v_organizations 
            WHERE from_date = ''2019-01-01'' AND to_date = ''2019-01-31''
        ) org ON CAST(bs.org_no AS TEXT) = org.organisasjonsnummer
        LEFT JOIN (
            SELECT
                organisasjonsnummer,
                navn AS suborg_name
            FROM v_suborganizations
            WHERE from_date = ''2019-01-01'' AND to_date = ''2019-01-31''
        ) suborg ON CAST(bs.suborg_no AS TEXT) = suborg.organisasjonsnummer
        WHERE bs.year_month = ''201901''
        LIMIT 0
        ';

        CREATE OR REPLACE VIEW u_site_org_consolidated 
        FOLDER = '/02_integration/transaction_segmentation' 
        DESCRIPTION = 'A union view to combine site_org tables per payment scheme.'  
        AS 
        SELECT run_id, year_month, site_id, transaction_source, merchant_id, text_line3 AS text_line, NULL AS dummy_col
        FROM iv_site_org_bax_pm 
        SQL 
        UNION 
        SELECT run_id, year_month, site_id, transaction_source, merchant_id, text_line3 AS text_line, NULL AS dummy_col
        FROM iv_site_org_visa_no;
        """
        mock_file.return_value.__enter__.return_value.read.return_value = vql_content
        edges, node_types, database_stats = parse_vql("dummy.vql")
        with open("res.txt", "w") as f:
            print(edges, node_types, file=f)

        # Assert that the table declaration is correctly parsed and classified.
        self.assertIn("iv_site_org_bax_pm", node_types)
        self.assertEqual(node_types["iv_site_org_bax_pm"].get("type"), "table")
        # For this test, since there is no database prefix, the database field should be empty.
        self.assertEqual(node_types["iv_site_org_bax_pm"].get("database"), "")

        # Assert that the view declaration is correctly parsed and classified.
        self.assertIn("u_site_org_consolidated", node_types)
        self.assertEqual(node_types["u_site_org_consolidated"].get("type"), "view")
        self.assertEqual(node_types["u_site_org_consolidated"].get("database"), "")

        # Check data flow edges from source to target
        # For the VIEW:
        self.assertIn(("iv_site_org_bax_pm", "u_site_org_consolidated"), edges)
        self.assertIn(("iv_site_org_visa_no", "u_site_org_consolidated"), edges)
        # For the TABLE's DATA_LOAD_QUERY, check data flow from source tables
        self.assertIn(("i_bv_business_site_bax_pm", "iv_site_org_bax_pm"), edges)
        self.assertIn(("i_bv_merchants_bax_pm_corrected", "iv_site_org_bax_pm"), edges)
        self.assertIn(("v_organizations", "iv_site_org_bax_pm"), edges)
        self.assertIn(("v_suborganizations", "iv_site_org_bax_pm"), edges)

if __name__ == "__main__":
    unittest.main()

