ARG BASE_IMAGE=benchmark-base:qiskit_nature_973_1018
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_973_1018
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/973
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/1018
ENV BASE_COMMIT=71c4c22a783ff39e1adc4f3f48943a3a1179c411
ENV PATCHED_COMMIT=575c24e18f6da34c5e3bdd055f322621ee2ddfdc
ENV PR_HEAD_COMMIT=575c24e18f6da34c5e3bdd055f322621ee2ddfdc
ENV FAIL_PASS_TEST_PATHS="test/second_q/mappers/test_parity_mapper.py::TestParityMapper::test_mapping_with_two_qubit_reduction test/second_q/mappers/test_qubit_converter.py::TestQubitConverter::test_paritymapper_two_qubit_reduction test/second_q/algorithms/excited_state_solvers/test_excited_states_solvers.py::TestNumericalQEOMESCCalculation::test_solve_with_vqe_mes_03_PM_TQR"
ENV PASS_PASS_TEST_PATHS="test/second_q/mappers/test_jordan_wigner_mapper.py::TestJordanWignerMapper::test_mapping test/second_q/mappers/test_bravyi_kitaev_mapper.py::TestBravyiKitaevMapper::test_mapping test/second_q/mappers/test_bksf_mapper.py::TestBravyiKitaevSuperFastMapper::test_h2 test/second_q/mappers/test_parity_mapper.py::TestParityMapper::test_allows_two_qubit_reduction test/second_q/mappers/test_parity_mapper.py::TestParityMapper::test_mapping_for_single_op test/second_q/mappers/test_qubit_converter.py::TestQubitConverter::test_mapping_basic test/second_q/mappers/test_qubit_converter.py::TestQubitConverter::test_two_qubit_reduction_and_z2_symmetry test/second_q/mappers/test_qubit_converter.py::TestQubitConverter::test_z2_symmetry"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
