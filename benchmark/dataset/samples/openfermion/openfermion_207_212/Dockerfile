ARG BASE_IMAGE=benchmark-base:openfermion_207_212
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_207_212
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/207
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/212
ENV BASE_COMMIT=6391cb79854c9510ed3a59f16244a077579f084d
ENV PATCHED_COMMIT=d7f462aeae97413b1b7a9ceb0eeddd07f6eec6ce
ENV PR_HEAD_COMMIT=d7f462aeae97413b1b7a9ceb0eeddd07f6eec6ce
ENV FAIL_PASS_TEST_PATHS="src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_freeze_orbitals_nonvanishing src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_freeze_orbitals_vanishing"
ENV PASS_PASS_TEST_PATHS="src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_normal_ordered_number_reversed src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_normal_ordered_offsite_reversed src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_normal_ordered_multi src/openfermion/ops/_fermion_operator_test.py::FermionOperatorTest::test_is_molecular_term_out_of_order"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
