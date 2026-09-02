package com.example.helloservice.controller;

import com.example.helloservice.feign.DateClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class HelloController {

    @Autowired
    private DateClient dateClient;

    @GetMapping("/")
    public String hello(Model model) {
        String date = dateClient.getDate();
        model.addAttribute("date", date);
        return "hello";
    }
}
