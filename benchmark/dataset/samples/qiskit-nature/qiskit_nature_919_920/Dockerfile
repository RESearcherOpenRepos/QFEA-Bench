ARG BASE_IMAGE=benchmark-base:qiskit_nature_919_920
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_919_920
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/919
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/920
ENV BASE_COMMIT=e3c8d4c60d39af91cf02a02aa805697f2166273a
ENV PATCHED_COMMIT=c393383e1203c2da1b57c3c0c8dde9b828030796
ENV PR_HEAD_COMMIT=c393383e1203c2da1b57c3c0c8dde9b828030796
ENV FAIL_PASS_TEST_PATHS="test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_from_orbital_occupation_1_True test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_from_orbital_occupation_2_False test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_second_q_ops_1_True test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_second_q_ops_2_False test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_interpret_1_True test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_interpret_2_False"
ENV PASS_PASS_TEST_PATHS="test/second_q/properties/test_particle_number.py::TestParticleNumber::test_second_q_ops test/second_q/properties/test_magnetization.py::TestMagnetization::test_second_q_ops test/second_q/properties/test_angular_momentum.py::TestAngularMomentum::test_second_q_ops"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
