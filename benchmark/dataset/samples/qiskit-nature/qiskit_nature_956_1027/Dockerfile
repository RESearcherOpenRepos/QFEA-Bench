ARG BASE_IMAGE=benchmark-base:qiskit_nature_956_1027
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_956_1027
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/956
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/1027
ENV BASE_COMMIT=0f73ea754c25fe549c37b1c4ccb51db381a57078
ENV PATCHED_COMMIT=660bfdba911a3b9226301e3ab22f4f99a03c595a
ENV PR_HEAD_COMMIT=660bfdba911a3b9226301e3ab22f4f99a03c595a
ENV FAIL_PASS_TEST_PATHS="test/second_q/hamiltonians/lattices/test_hexagonal_lattice.py::TestHexagonalLattice::test_init"
ENV PASS_PASS_TEST_PATHS="test/second_q/hamiltonians/lattices/test_hyper_cubic_lattice.py::TestHyperCubic::test_init test/second_q/hamiltonians/lattices/test_kagome_lattice.py::TestKagomeLattice::test_init_open test/second_q/hamiltonians/lattices/test_kagome_lattice.py::TestKagomeLattice::test_init_periodic test/second_q/hamiltonians/lattices/test_kagome_lattice.py::TestKagomeLattice::test_init_x_periodic test/second_q/hamiltonians/lattices/test_kagome_lattice.py::TestKagomeLattice::test_init_y_periodic test/second_q/hamiltonians/lattices/test_lattice.py::TestLattice::test_copy test/second_q/hamiltonians/lattices/test_lattice.py::TestLattice::test_edges_removed test/second_q/hamiltonians/lattices/test_lattice.py::TestLattice::test_from_nodes_and_edges test/second_q/hamiltonians/lattices/test_lattice.py::TestLattice::test_init test/second_q/hamiltonians/lattices/test_lattice.py::TestLattice::test_nonnumeric_weight_raises test/second_q/hamiltonians/lattices/test_lattice.py::TestLattice::test_to_adjacency_matrix test/second_q/hamiltonians/lattices/test_line_lattice.py::TestLineLattice::test_init test/second_q/hamiltonians/lattices/test_square_lattice.py::TestSquareLattice::test_init test/second_q/hamiltonians/lattices/test_triangular_lattice.py::TestTriangularLattice::test_init_open test/second_q/hamiltonians/lattices/test_triangular_lattice.py::TestTriangularLattice::test_init_periodic"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
