package com.example.iot.pose.model;

/**
 * 2D keypoint (image coords) + confidence.
 * (x: right+, y: down+) 가정.
 */
public record Point2D(double x, double y, double conf) {
}