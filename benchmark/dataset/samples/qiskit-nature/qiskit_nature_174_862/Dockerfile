ARG BASE_IMAGE=benchmark-base:qiskit_nature_174_862
FROM ${BASE_IMAGE}

ENV SAMPLE_ID=qiskit_nature_174_862
ENV REPOSITORY=qiskit-community/qiskit-nature
ENV REPOSITORY_URL=https://github.com/qiskit-community/qiskit-nature.git
ENV ISSUE_URL=https://github.com/qiskit-community/qiskit-nature/issues/174
ENV PR_URL=https://github.com/qiskit-community/qiskit-nature/pull/862
ENV BASE_COMMIT=8b213070389760724b88ee9b3497711de34397f4
ENV PATCHED_COMMIT=53aa83650ae55bd287622a88aaa88dd70d08e3ea
ENV PR_HEAD_COMMIT=53aa83650ae55bd287622a88aaa88dd70d08e3ea
ENV FAIL_PASS_TEST_PATHS="test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_from_orbital_occupation test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_second_q_ops test/second_q/properties/test_electronic_density.py::TestElectronicDensity::test_interpret"
ENV PASS_PASS_TEST_PATHS="test/second_q/problems/test_electronic_properties_container.py::TestElectronicPropertiesContainer::test_angular_momentum test/second_q/problems/test_electronic_properties_container.py::TestElectronicPropertiesContainer::test_electronic_dipole_moment test/second_q/problems/test_electronic_properties_container.py::TestElectronicPropertiesContainer::test_magnetization test/second_q/problems/test_electronic_properties_container.py::TestElectronicPropertiesContainer::test_particle_number test/second_q/problems/test_electronic_properties_container.py::TestElectronicPropertiesContainer::test_custom_property test/second_q/operators/test_electronic_integrals.py::TestElectronicIntegrals::test_attributes test/second_q/operators/test_electronic_integrals.py::TestElectronicIntegrals::test_one_body test/second_q/operators/test_electronic_integrals.py::TestElectronicIntegrals::test_two_body test/second_q/operators/test_electronic_integrals.py::TestElectronicIntegrals::test_iter test/second_q/operators/test_electronic_integrals.py::TestElectronicIntegrals::test_add test/second_q/operators/test_electronic_integrals.py::TestElectronicIntegrals::test_conjugate test/second_q/operators/test_electronic_integrals.py::TestElectronicIntegrals::test_transpose"
ENV DEFAULT_TARGET=patched

COPY sample.json /benchmark/sample.json
COPY run.sh /benchmark/run.sh
RUN chmod +x /benchmark/run.sh

ENTRYPOINT ["/benchmark/run.sh"]
CMD ["patched"]
