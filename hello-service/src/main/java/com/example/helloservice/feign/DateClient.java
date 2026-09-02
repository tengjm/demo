package com.example.helloservice.feign;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;

@FeignClient(name = "date-service")
public interface DateClient {

    @GetMapping("/api/date")
    String getDate();
}
