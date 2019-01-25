#!/usr/bin/env groovy

@Library('sec_ci_libs@v2-latest') _

pipeline {
  agent none

  options {
    timeout(time: 2, unit: 'HOURS')
  }

  stages {
    stage("Update https://downloads.dcos.io/cli/index.html") {
      agent { label 'py36' }

      steps {
        withCredentials([
            string(credentialsId: "1ddc25d8-0873-4b6f-949a-ae803b074e7a",variable: "AWS_ACCESS_KEY_ID"),
            string(credentialsId: "875cfce9-90ca-4174-8720-816b4cb7f10f",variable: "AWS_SECRET_ACCESS_KEY"),
        ]) {
            sh '''
              bash -exc " \
                cd ci; \
                python -m venv env; \
                source env/bin/activate; \
                pip install --upgrade pip setuptools; \
                pip install -r requirements.txt; \
                cd index; \
                ./publish_artifacts.py"
            '''
        }
      }
    }
  }
}
