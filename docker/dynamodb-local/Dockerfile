# DynamoDB Local on Amazon Corretto (AWS's OpenJDK distribution) rather than a stock JDK image.
FROM amazoncorretto:21
RUN yum install -y -q tar gzip && yum clean all \
 && mkdir /opt/dynamodb && cd /opt/dynamodb \
 && curl -sSfL https://d1ni2b6xgvw0s0.cloudfront.net/v2.x/dynamodb_local_latest.tar.gz | tar xz
WORKDIR /opt/dynamodb
EXPOSE 8000
CMD ["java", "-Djava.library.path=./DynamoDBLocal_lib", "-jar", "DynamoDBLocal.jar", "-sharedDb", "-inMemory"]
