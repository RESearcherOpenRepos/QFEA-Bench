ARG BASE_IMAGE=benchmark-base:qiskit_nature_865_890
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_865_890
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/865
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/890
ENV BASE_COMMIT=3f36886cbacc26cd68c3179c9e224ee87906640f
ENV PATCHED_COMMIT=92a0b86bddf48c52f5b359e69e020031aa38488a
ENV PR_HEAD_COMMIT=92a0b86bddf48c52f5b359e69e020031aa38488a
ENV FAIL_PASS_TEST_PATHS="test/second_q/hamiltonians/test_quadratic_hamiltonian.py::TestQuadraticHamiltonian::test_addition test/second_q/hamiltonians/test_quadratic_hamiltonian.py::TestQuadraticHamiltonian::test_multiplication test/second_q/hamiltonians/test_quadratic_hamiltonian.py::TestQuadraticHamiltonian::test_repr"
ENV PASS_PASS_TEST_PATHS="test/second_q/hamiltonians/test_quadratic_hamiltonian.py::TestQuadraticHamiltonian::test_init test/second_q/hamiltonians/test_quadratic_hamiltonian.py::TestQuadraticHamiltonian::test_fermionic_op test/second_q/hamiltonians/test_quadratic_hamiltonian.py::TestQuadraticHamiltonian::test_validate"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
