ARG BASE_IMAGE=benchmark-base:qiskit_nature_563_620
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_563_620
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/563
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/620
ENV BASE_COMMIT=f29f54f3962d9a30345ffb8f98d87d4c985bc71c
ENV PATCHED_COMMIT=e9fc62d3dc9f4aa05130dc910ee5764e85ca38a7
ENV PR_HEAD_COMMIT=e9fc62d3dc9f4aa05130dc910ee5764e85ca38a7
ENV FAIL_PASS_TEST_PATHS="test/problems/second_quantization/lattice/test_lattice_model_problem.py::TestLatticeModelProblem::test_second_q_ops test/problems/second_quantization/lattice/test_lattice_model_problem.py::TestLatticeModelProblem::test_interpret"
ENV PASS_PASS_TEST_PATHS="test/problems/second_quantization/lattice/models/test_fermi_hubbard_model.py::TestFermiHubbardModel::test_init test/problems/second_quantization/lattice/models/test_fermi_hubbard_model.py::TestFermiHubbardModel::test_uniform_parameters test/problems/second_quantization/lattice/models/test_fermi_hubbard_model.py::TestFermiHubbardModel::test_from_parameters"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
