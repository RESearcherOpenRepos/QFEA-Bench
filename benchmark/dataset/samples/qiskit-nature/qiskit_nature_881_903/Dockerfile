ARG BASE_IMAGE=benchmark-base:qiskit_nature_881_903
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_881_903
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/881
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/903
ENV BASE_COMMIT=417d7792470c36ebfef5444c9895fe5985b558fc
ENV PATCHED_COMMIT=729723bd4be61d1eb1b952613dbea04bfbce77d7
ENV PR_HEAD_COMMIT=729723bd4be61d1eb1b952613dbea04bfbce77d7
ENV FAIL_PASS_TEST_PATHS="test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_qubits_4_jw_h2_lazy_attribute_setting test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_raises_on_unsupported_mapper test/second_q/circuit/library/initial_states/test_vscf.py::TestVSCF::test_qubits_6_lazy_attribute_setting"
ENV PASS_PASS_TEST_PATHS="test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_bitstring test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_bitstring_invalid_input test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_hf_bitstring_mapped test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_qubits_2_py_h2 test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_qubits_4_bk_h2 test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_qubits_4_jw_h2 test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_qubits_4_py_h2 test/second_q/circuit/library/initial_states/test_hartree_fock.py::TestHartreeFock::test_qubits_6_py_lih test/second_q/circuit/library/initial_states/test_vscf.py::TestVSCF::test_bitstring test/second_q/circuit/library/initial_states/test_vscf.py::TestVSCF::test_qubits_4 test/second_q/circuit/library/initial_states/test_vscf.py::TestVSCF::test_qubits_5"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
