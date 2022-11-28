FROM openjdk:18
ADD aws-lambda-demo-producer.jar aws-lambda-demo-producer.jar
COPY cloud.config cloud.config
ENTRYPOINT ["java", "-jar","aws-lambda-demo-producer.jar"]