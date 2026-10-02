FROM benchmark-base:qiskit_nature_167_220

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_167_220
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/167
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/220
ENV BASE_COMMIT=bc2162b5e09bdb793678dfde816041f90a81205b
ENV PATCHED_COMMIT=b4a46bf49408153603c3d24bfccc15ceb94aac82
ENV PR_HEAD_COMMIT=b4a46bf49408153603c3d24bfccc15ceb94aac82
ENV FAIL_PASS_TEST_PATHS="test/properties/second_quantization/electronic/test_particle_number.py::TestParticleNumber::test_second_q_ops test/properties/second_quantization/electronic/test_magnetization.py::TestMagnetization::test_second_q_ops test/properties/second_quantization/electronic/test_angular_momentum.py::TestAngularMomentum::test_second_q_ops"
ENV PASS_PASS_TEST_PATHS="test/problems/second_quantization/electronic/test_electronic_structure_problem.py::TestElectronicStructureProblem::test_second_q_ops_without_transformers test/problems/second_quantization/electronic/test_electronic_structure_problem.py::TestElectronicStructureProblem::test_second_q_ops_with_active_space test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_npme test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_eval_op_single test/algorithms/ground_state_solvers/test_groundstate_eigensolver.py::TestGroundStateEigensolver::test_eval_op_list"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
