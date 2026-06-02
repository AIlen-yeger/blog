package com.personalblog.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import com.personalblog.security.JwtAuthInterceptor;
import com.personalblog.security.QuietHoursInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@RequiredArgsConstructor
public class WebConfig implements WebMvcConfigurer {

    private final JwtAuthInterceptor jwtAuthInterceptor;
    private final QuietHoursInterceptor quietHoursInterceptor;

    @Value("${app.cors.allowed-origins}")
    private String allowedOrigins;

    @Value("${app.upload.avatar-dir}")
    private String avatarDir;

    @Value("${app.upload.content-dir}")
    private String contentDir;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(jwtAuthInterceptor)
                .addPathPatterns("/**")
                .order(0);
        registry.addInterceptor(quietHoursInterceptor)
                .addPathPatterns("/**")
                .order(1);
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/**")
                .allowedOrigins(allowedOrigins.split(","))
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true);
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        String location = "file:" + avatarDir.replace("\\", "/") + "/";
        registry.addResourceHandler("/uploads/avatars/**").addResourceLocations(location);
        String contentLocation = "file:" + contentDir.replace("\\", "/") + "/";
        registry.addResourceHandler("/uploads/content/**").addResourceLocations(contentLocation);
    }
}
