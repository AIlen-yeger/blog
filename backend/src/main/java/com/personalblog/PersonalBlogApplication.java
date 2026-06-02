package com.personalblog;

import com.personalblog.config.AgentProperties;
import com.personalblog.config.AgentReplyProperties;
import com.personalblog.config.ContentViewProperties;
import com.personalblog.config.QuietHoursProperties;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@MapperScan("com.personalblog.mapper")
@EnableScheduling
@EnableAsync
@EnableConfigurationProperties({
        ContentViewProperties.class,
        AgentProperties.class,
        AgentReplyProperties.class,
        QuietHoursProperties.class
})
public class PersonalBlogApplication {

    public static void main(String[] args) {
        SpringApplication.run(PersonalBlogApplication.class, args);
    }
}
