FROM benchmark-base:qiskit_nature_42_49

WORKDIR /workspace

ENV SAMPLE_ID=qiskit_nature_42_49
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/42
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/49
ENV BASE_COMMIT=5351294e03a15b1d0ccd4012b4313c8236729b49
ENV PATCHED_COMMIT=c71dff0e47b09005c21dc2690833e61e42686997
ENV PR_HEAD_COMMIT=c71dff0e47b09005c21dc2690833e61e42686997
ENV FAIL_PASS_TEST_PATHS="test/problems/second_quantization/molecular/test_molecular_problem.py::TestMolecularProblem::test_second_q_ops_without_transformers test/problems/second_quantization/molecular/test_molecular_problem.py::TestMolecularProblem::test_second_q_ops_with_active_space"
ENV PASS_PASS_TEST_PATHS="test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_minimal_active_space test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_arbitrary_active_orbitals test/transformers/test_active_space_transformer.py::TestActiveSpaceTransformer::test_active_space_for_q_molecule_v2 test/operators/test_fermionic_op.py::TestFermionicOp::test_init_multiterm test/operators/test_fermionic_op.py::TestFermionicOp::test_add test/operators/test_fermionic_op.py::TestFermionicOp::test_reduce"
ENV FAIL_PASS_EXTRA_FILES="test/problems/__init__.py test/problems/second_quantization/__init__.py test/problems/second_quantization/molecular/__init__.py test/problems/second_quantization/molecular/resources/__init__.py test/problems/second_quantization/molecular/resources/resource_reader.py test/problems/second_quantization/molecular/resources/H2_631g_ferm_op_two_ints test/problems/second_quantization/molecular/resources/H2_631g_ferm_op_active_space"

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
