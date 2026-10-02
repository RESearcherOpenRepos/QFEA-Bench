ARG BASE_IMAGE=benchmark-base:openfermion_458_501
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_458_501
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/458
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/501
ENV BASE_COMMIT=2789aecbb3e5b1aeebead434b73e4605c3864f83
ENV PATCHED_COMMIT=6fb280c9d223522ed5ce5e90f5cd809beda7f177
ENV PR_HEAD_COMMIT=6fb280c9d223522ed5ce5e90f5cd809beda7f177
ENV FAIL_PASS_TEST_PATHS="src/openfermion/ops/_majorana_operator_test.py::test_majorana_operator_init src/openfermion/ops/_majorana_operator_test.py::test_majorana_operator_commutes_with src/openfermion/ops/_majorana_operator_test.py::test_majorana_operator_multiply src/openfermion/ops/_majorana_operator_test.py::test_majorana_operator_divide src/openfermion/ops/_majorana_operator_test.py::test_majorana_operator_str"
ENV PASS_PASS_TEST_PATHS="src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_init_tuple_complex_coefficient src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_zero_is_additive_identity src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_mul_out_of_place src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest1::test_iadd_different_term src/openfermion/ops/_symbolic_operator_test.py::SymbolicOperatorTest2::test_str_multiple_terms"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
