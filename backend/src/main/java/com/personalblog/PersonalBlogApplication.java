package com.personalblog;

import com.personalblog.config.AgentProperties;
import com.personalblog.config.ContentViewProperties;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@MapperScan("com.personalblog.mapper")
@EnableScheduling
@EnableConfigurationProperties({ContentViewProperties.class, AgentProperties.class})
public class PersonalBlogApplication {

    public static void main(String[] args) {
        SpringApplication.run(PersonalBlogApplication.class, args);
    }
}
