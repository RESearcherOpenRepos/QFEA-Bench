ARG BASE_IMAGE=benchmark-base:qiskit_nature_252_318
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_252_318
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/252
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/318
ENV BASE_COMMIT=580183c6f8da4a8cb9f6a408ab3e7861be27c495
ENV PATCHED_COMMIT=0266d2baffcf7f1f8b710659adcfea509f732602
ENV PR_HEAD_COMMIT=0266d2baffcf7f1f8b710659adcfea509f732602
ENV FAIL_PASS_TEST_PATHS="test/problems/sampling/protein_folding/test_protein_folding_problem.py::TestProteinFoldingProblem::test_protein_folding_problem_2_second_bead_side_chain test/problems/sampling/protein_folding/qubit_utils/test_qubit_fixing.py::TestQubitFixing::test_fix_qubits_large_fifth_qubit_allowed"
ENV PASS_PASS_TEST_PATHS="test/problems/sampling/protein_folding/test_protein_folding_problem.py::TestProteinFoldingProblem::test_protein_folding_problem test/problems/sampling/protein_folding/qubit_utils/test_qubit_fixing.py::TestQubitFixing::test_fix_qubits_small test/problems/sampling/protein_folding/qubit_utils/test_qubit_fixing.py::TestQubitFixing::test_fix_qubits_small_2 test/problems/sampling/protein_folding/qubit_utils/test_qubit_fixing.py::TestQubitFixing::test_fix_qubits_large test/problems/sampling/protein_folding/qubit_utils/test_qubit_fixing.py::TestQubitFixing::test_fix_qubits_pauli_op test/problems/sampling/protein_folding/peptide/chains/test_chain_main.py::TestMainChain::test_main_chain_constructor test/problems/sampling/protein_folding/peptide/chains/test_chain_main.py::TestMainChain::test_main_chain_illegal_side_chain_first test/problems/sampling/protein_folding/peptide/chains/test_chain_main.py::TestMainChain::test_main_chain_illegal_side_chain_last"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
