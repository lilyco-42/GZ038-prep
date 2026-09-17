package com.env.newland.envmonitor;

import java.io.Serializable;

/**
 * 规则数据类。
 * sensor   传感器（温度/湿度/光照/人体）
 * op       比较运算符（大于/小于/等于/不等于）
 * threshold 阈值
 * actuator 执行器（绿灯/LED灯/风扇）
 */
public class Rule implements Serializable {

    private static final long serialVersionUID = 1L;

    public String sensor;
    public String op;
    public double threshold;
    public String actuator;

    public Rule() {
    }

    public Rule(String sensor, String op, double threshold, String actuator) {
        this.sensor = sensor;
        this.op = op;
        this.threshold = threshold;
        this.actuator = actuator;
    }

    /**
     * 用指定传感器数值对规则求值。
     * 大于: v > threshold；小于: v < threshold；
     * 等于: |v - threshold| <= 0.01；不等于: |v - threshold| > 0.01。
     */
    public boolean matches(double value) {
        if (op == null) {
            return false;
        }
        if ("大于".equals(op)) {
            return value > threshold;
        }
        if ("小于".equals(op)) {
            return value < threshold;
        }
        if ("等于".equals(op)) {
            return Math.abs(value - threshold) <= 0.01;
        }
        if ("不等于".equals(op)) {
            return Math.abs(value - threshold) > 0.01;
        }
        return false;
    }

    @Override
    public String toString() {
        return sensor + " " + op + " " + formatNumber(threshold) + " \u2192 " + actuator;
    }

    private static String formatNumber(double v) {
        if (v == Math.floor(v) && !Double.isInfinite(v) && Math.abs(v) < 1e12) {
            return String.valueOf((long) v);
        }
        return String.valueOf(v);
    }
}