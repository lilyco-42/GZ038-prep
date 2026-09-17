package com.env.newland.envmonitor;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.RectF;
import android.util.AttributeSet;
import android.view.View;

/**
 * 圆形仪表盘自定义 View：外圈彩色圆环 + 顶部标签 + 中心数值。
 * 通过 setGauge(int ringColor, String label, String value) 设置。
 */
public class CircularGaugeView extends View {

    private final Paint ringPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint bgRingPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint labelPaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint valuePaint = new Paint(Paint.ANTI_ALIAS_FLAG);

    private int ringColor = Color.CYAN;
    private String label = "";
    private String value = "0";
    private final RectF oval = new RectF();

    public CircularGaugeView(Context context) {
        super(context);
        init();
    }

    public CircularGaugeView(Context context, AttributeSet attrs) {
        super(context, attrs);
        init();
    }

    public CircularGaugeView(Context context, AttributeSet attrs, int defStyleAttr) {
        super(context, attrs, defStyleAttr);
        init();
    }

    private void init() {
        ringPaint.setStyle(Paint.Style.STROKE);
        ringPaint.setStrokeCap(Paint.Cap.ROUND);

        bgRingPaint.setStyle(Paint.Style.STROKE);
        bgRingPaint.setColor(Color.argb(40, 255, 255, 255));

        labelPaint.setColor(Color.WHITE);
        labelPaint.setTextAlign(Paint.Align.CENTER);

        valuePaint.setColor(Color.WHITE);
        valuePaint.setTextAlign(Paint.Align.CENTER);
        valuePaint.setFakeBoldText(true);
    }

    public void setGauge(int ringColor, String label, String value) {
        this.ringColor = ringColor;
        this.label = label;
        this.value = value;
        invalidate();
    }

    public void setValue(String value) {
        this.value = value;
        invalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        int w = getWidth();
        int h = getHeight();
        int cx = w / 2;
        int cy = h / 2;
        float radius = Math.min(cx, cy) * 0.82f;
        float strokeWidth = radius * 0.10f;

        // 背景圆环
        bgRingPaint.setStrokeWidth(strokeWidth);
        oval.set(cx - radius, cy - radius, cx + radius, cy + radius);
        canvas.drawArc(oval, 0, 360, false, bgRingPaint);

        // 彩色圆环
        ringPaint.setStrokeWidth(strokeWidth);
        ringPaint.setColor(ringColor);
        canvas.drawArc(oval, -90, 360, false, ringPaint);

        // 顶部标签
        labelPaint.setTextSize(radius * 0.28f);
        float labelY = cy - radius * 0.18f;
        canvas.drawText(label, cx, labelY, labelPaint);

        // 中心数值
        valuePaint.setTextSize(radius * 0.52f);
        valuePaint.setColor(ringColor);
        float valueY = cy + radius * 0.38f;
        canvas.drawText(value, cx, valueY, valuePaint);
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        int w = MeasureSpec.getSize(widthMeasureSpec);
        int h = MeasureSpec.getSize(heightMeasureSpec);
        int size = Math.min(w, h);
        setMeasuredDimension(size, size);
    }
}
