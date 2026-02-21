"""Tests for JUnit XML parsing into TieredScore."""

from pathlib import Path

import pytest

from ate_features.scoring import parse_junit_xml

SAMPLE_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="4" skipped="0" tests="13">
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT1Basic"
              name="test_dataframe_round_trip" time="0.01">
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT1Basic"
              name="test_series_round_trip" time="0.01">
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT1Basic"
              name="test_no_pickle_fallback" time="0.01">
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT2EdgeCases"
              name="test_multiindex" time="0.01">
      <failure message="assert False">AssertionError</failure>
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT2EdgeCases"
              name="test_mixed_dtypes" time="0.01">
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT2EdgeCases"
              name="test_empty" time="0.01">
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT2EdgeCases"
              name="test_named_index" time="0.01">
      <failure message="assert False">AssertionError</failure>
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT2EdgeCases"
              name="test_nan" time="0.01">
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT3Quality"
              name="test_dtype_preservation" time="0.01">
      <failure message="assert False">AssertionError</failure>
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT3Quality"
              name="test_performance" time="0.01">
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT3Quality"
              name="test_multiindex_columns" time="0.01">
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT4Smoke"
              name="test_checkpoint" time="0.01">
      <failure message="assert False">AssertionError</failure>
    </testcase>
    <testcase classname="tests.acceptance.test_f1_pandas_serde.TestT4Smoke"
              name="test_graph_execution" time="0.01">
    </testcase>
  </testsuite>
</testsuites>
"""


@pytest.fixture
def xml_path(tmp_path: Path) -> Path:
    path = tmp_path / "results.xml"
    path.write_text(SAMPLE_XML)
    return path


class TestParseJunitXml:
    def test_parses_tier_counts(self, xml_path: Path) -> None:
        score = parse_junit_xml(xml_path, "F1", "0a")
        assert score.t1_passed == 3
        assert score.t1_total == 3
        assert score.t2_passed == 3
        assert score.t2_total == 5
        assert score.t3_passed == 2
        assert score.t3_total == 3
        assert score.t4_passed == 1
        assert score.t4_total == 2

    def test_sets_feature_and_treatment(self, xml_path: Path) -> None:
        score = parse_junit_xml(xml_path, "F1", "0a")
        assert score.feature_id == "F1"
        assert score.treatment_id == "0a"

    def test_all_passing(self, tmp_path: Path) -> None:
        xml = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="0" failures="0" tests="3">
    <testcase classname="test.TestT1Basic" name="a" time="0.01"/>
    <testcase classname="test.TestT2EdgeCases" name="b" time="0.01"/>
    <testcase classname="test.TestT3Quality" name="c" time="0.01"/>
  </testsuite>
</testsuites>
"""
        path = tmp_path / "all_pass.xml"
        path.write_text(xml)
        score = parse_junit_xml(path, "F2", 1)
        assert score.t1_passed == 1
        assert score.t1_total == 1
        assert score.t2_passed == 1
        assert score.t3_passed == 1
        assert score.t4_passed == 0
        assert score.t4_total == 0

    def test_all_failing(self, tmp_path: Path) -> None:
        xml = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="2">
    <testcase classname="test.TestT1Basic" name="a">
      <failure>fail</failure>
    </testcase>
    <testcase classname="test.TestT1Basic" name="b">
      <failure>fail</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
        path = tmp_path / "all_fail.xml"
        path.write_text(xml)
        score = parse_junit_xml(path, "F3", "2a")
        assert score.t1_passed == 0
        assert score.t1_total == 2

    def test_error_counts_as_failure(self, tmp_path: Path) -> None:
        xml = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="1">
    <testcase classname="test.TestT1Basic" name="a">
      <error>error</error>
    </testcase>
  </testsuite>
</testsuites>
"""
        path = tmp_path / "error.xml"
        path.write_text(xml)
        score = parse_junit_xml(path, "F4", 3)
        assert score.t1_passed == 0
        assert score.t1_total == 1

    def test_unknown_tier_ignored(self, tmp_path: Path) -> None:
        xml = """\
<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="2">
    <testcase classname="test.TestT1Basic" name="a"/>
    <testcase classname="test.SomeOtherClass" name="b"/>
  </testsuite>
</testsuites>
"""
        path = tmp_path / "unknown.xml"
        path.write_text(xml)
        score = parse_junit_xml(path, "F1", "0a")
        assert score.t1_total == 1
        assert score.t2_total == 0
