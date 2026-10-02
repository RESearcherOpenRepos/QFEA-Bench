ARG BASE_IMAGE=benchmark-base:qiskit_nature_91_729
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_91_729
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/91
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/729
ENV BASE_COMMIT=fbf11ddc9bcb0ca1e1413fbc69e53cc9d112e03b
ENV PATCHED_COMMIT=d59bab1f54a28c902818da4600e62cca7cbbfd57
ENV FAIL_PASS_TEST_PATHS="test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succ_mirror_1 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succ_mirror_ansatz_generalized_1 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succ_mirror_with_singles_1 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succ_mirror_with_singles_2 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succ_mirror_with_singles_3"
ENV PASS_PASS_TEST_PATHS="test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_puccd_ansatz_generalized_1 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_puccd_ansatz_generalized_2 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_raise_non_singlet test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succd_ansatz_1 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succd_ansatz_2 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succd_ansatz_with_singles_1 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succd_ansatz_with_singles_2 test/second_q/circuit/library/ansatzes/test_succd.py::TestSUCCD::test_succd_ansatz_with_singles_3"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
