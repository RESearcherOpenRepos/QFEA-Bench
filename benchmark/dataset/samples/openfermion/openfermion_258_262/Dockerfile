ARG BASE_IMAGE=benchmark-base:openfermion_258_262
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=openfermion_258_262
ENV REPOSITORY=quantumlib/OpenFermion
ENV REPOSITORY_URL=https://github.com/quantumlib/OpenFermion.git
ENV ISSUE_URL=https://github.com/quantumlib/OpenFermion/issues/258
ENV PR_URL=https://github.com/quantumlib/OpenFermion/pull/262
ENV BASE_COMMIT=46ce88bac2dee2cb4b5abca17e9202975f0c8b3e
ENV PATCHED_COMMIT=98134afd34f2591aaac851005ae057cdff8457d2
ENV PR_HEAD_COMMIT=98134afd34f2591aaac851005ae057cdff8457d2
ENV FAIL_PASS_TEST_PATHS="src/openfermion/utils/_special_operators_test.py::MajoranaOperatorTest::test_init src/openfermion/ops/_quadratic_hamiltonian_test.py::QuadraticHamiltoniansTest::test_majorana_form"
ENV PASS_PASS_TEST_PATHS="src/openfermion/utils/_special_operators_test.py::FermionSpinOperatorsTest::test_sz_operator src/openfermion/utils/_special_operators_test.py::FermionSpinOperatorsTest::test_s_plus_operator src/openfermion/utils/_special_operators_test.py::FermionSpinOperatorsTest::test_s_minus_operator src/openfermion/utils/_special_operators_test.py::FermionSpinOperatorsTest::test_s_squared_operator src/openfermion/ops/_quadratic_hamiltonian_test.py::QuadraticHamiltoniansTest::test_ground_energy src/openfermion/transforms/_verstraete_cirac_test.py::VerstraeteCirac2dSquareOperatorLocalityTest::test_operator_locality_no_aux"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
