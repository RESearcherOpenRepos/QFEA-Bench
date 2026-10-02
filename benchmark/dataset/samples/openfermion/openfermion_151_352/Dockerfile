ARG BASE_IMAGE=benchmark-base:openfermion_151_352
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_151_352
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/151
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/352
ENV BASE_COMMIT=961f6482cec94430bb2a8c863cdb42e85425cd7d
ENV PATCHED_COMMIT=9dc86d3ca034dac3b0a6e02b67f87038fb962ed0
ENV PR_HEAD_COMMIT=9dc86d3ca034dac3b0a6e02b67f87038fb962ed0
ENV FAIL_PASS_TEST_PATHS="src/openfermion/ops/_boson_operator_test.py::BosonOperatorTest::test_is_normal_ordered_empty src/openfermion/ops/_boson_operator_test.py::BosonOperatorTest::test_is_normal_ordered_number src/openfermion/ops/_boson_operator_test.py::BosonOperatorTest::test_is_normal_ordered_reversed src/openfermion/ops/_boson_operator_test.py::BosonOperatorTest::test_is_boson_preserving_BosonOperator src/openfermion/ops/_boson_operator_test.py::BosonOperatorTest::test_is_boson_preserving_out_of_order"
ENV PASS_PASS_TEST_PATHS="src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_is_normal_ordered_empty src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_is_normal_ordered_number src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_is_normal_ordered_reversed src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_is_normal_ordered_multi src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_is_normal_ordered_multiorder"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
