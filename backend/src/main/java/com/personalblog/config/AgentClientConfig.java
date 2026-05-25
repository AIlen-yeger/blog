package com.personalblog.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.net.http.HttpClient;
import java.time.Duration;

@Configuration
public class AgentClientConfig {

    @Bean
    public HttpClient agentHttpClient(AgentProperties agentProperties) {
        return HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(agentProperties.getConnectTimeoutMs()))
                .build();
    }
}
