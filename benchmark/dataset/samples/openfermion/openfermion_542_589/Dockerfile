ARG BASE_IMAGE=benchmark-base:openfermion_542_589
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_542_589
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/542
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/589
ENV BASE_COMMIT=54d28a8228bc1a2d9b5a31d6f827084e364b0942
ENV PATCHED_COMMIT=45d25cdd373d50f82dab9a9a7d6accdb0eecffb1
ENV PR_HEAD_COMMIT=45d25cdd373d50f82dab9a9a7d6accdb0eecffb1
ENV FAIL_PASS_TEST_PATHS="src/openfermion/transforms/_conversion_test.py::GetMajoranaOperatorTest::test_raises src/openfermion/transforms/_conversion_test.py::GetMajoranaOperatorTest::test_get_majorana_operator_fermion_operator src/openfermion/transforms/_conversion_test.py::GetMajoranaOperatorTest::test_get_majorana_operator_diagonalcoulomb"
ENV PASS_PASS_TEST_PATHS="src/openfermion/transforms/_conversion_test.py::GetDiagonalCoulombHamiltonianTest::test_hubbard src/openfermion/transforms/_conversion_test.py::GetDiagonalCoulombHamiltonianTest::test_random_quadratic src/openfermion/transforms/_conversion_test.py::GetDiagonalCoulombHamiltonianTest::test_ignore_incompatible_terms src/openfermion/transforms/_conversion_test.py::GetDiagonalCoulombHamiltonianTest::test_exceptions src/openfermion/transforms/_conversion_test.py::test_get_fermion_operator_majorana_operator"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
