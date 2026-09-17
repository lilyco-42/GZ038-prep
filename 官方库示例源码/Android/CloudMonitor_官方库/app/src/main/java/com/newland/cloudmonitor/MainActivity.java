package com.newland.cloudmonitor;

/**
 * 远程监控应用开发（子任务2-4）——官方库版（云平台）
 *
 * 仿照官方例程 nlecloudII 模板重写：
 *   1. NetWorkBusiness 登录物联网云平台（https://api.nlecloud.com/）
 *   2. 获取项目传感器实时数据（getSensors）
 *   3. 发送设备控制指令（control）
 *
 * 依赖：app/libs/nle_cloudsdk_v1.jar（官方二进制，U盘/官方例程 依赖/nle_cloudsdk 目录获取）
 */

import android.annotation.SuppressLint;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import java.util.List;

import cn.com.newland.nle_sdk.requestEntity.SignIn;
import cn.com.newland.nle_sdk.responseEntity.SensorInfo;
import cn.com.newland.nle_sdk.responseEntity.User;
import cn.com.newland.nle_sdk.responseEntity.base.BaseResponseEntity;
import cn.com.newland.nle_sdk.util.NCallBack;
import cn.com.newland.nle_sdk.util.NetWorkBusiness;

@SuppressLint("SetTextI18n")
public class MainActivity extends AppCompatActivity implements View.OnClickListener {

    private static final String TAG = "CloudMonitor";
    private static final String BASE_URL = "https://api.nlecloud.com/";

    private NetWorkBusiness netWorkBusiness;

    private EditText userEdit, pwdEdit, projectEdit;
    private TextView dataText;
    private Button loginBtn, queryBtn, controlOnBtn, controlOffBtn;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_main);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });
        getWindow().setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_HIDDEN);

        userEdit = findViewById(R.id.userEdit);
        pwdEdit = findViewById(R.id.pwdEdit);
        projectEdit = findViewById(R.id.projectEdit);
        dataText = findViewById(R.id.dataText);
        loginBtn = findViewById(R.id.loginBtn);
        queryBtn = findViewById(R.id.queryBtn);
        controlOnBtn = findViewById(R.id.controlOnBtn);
        controlOffBtn = findViewById(R.id.controlOffBtn);

        loginBtn.setOnClickListener(this);
        queryBtn.setOnClickListener(this);
        controlOnBtn.setOnClickListener(this);
        controlOffBtn.setOnClickListener(this);
    }

    /** 登录云平台（官方 nlecloudII 模板写法） */
    private void signIn() {
        String user = userEdit.getText().toString().trim();
        String pwd = pwdEdit.getText().toString().trim();
        netWorkBusiness = new NetWorkBusiness("", BASE_URL);
        netWorkBusiness.signIn(new SignIn(user, pwd), new NCallBack<BaseResponseEntity<User>>(getApplicationContext()) {
            @Override
            protected void onResponse(BaseResponseEntity<User> userBaseResponseEntity) {
                if (userBaseResponseEntity.getResultObj() == null) {
                    Toast.makeText(getApplication(), "登录失败：" + userBaseResponseEntity.getMessage(), Toast.LENGTH_SHORT).show();
                    return;
                }
                String accessToken = userBaseResponseEntity.getResultObj().getAccessToken();
                Log.d(TAG, "AccessToken: " + accessToken);
                // 使用 token 重建业务对象（官方模板写法）
                netWorkBusiness = new NetWorkBusiness(accessToken, BASE_URL);
                Toast.makeText(getApplication(), "登录成功", Toast.LENGTH_SHORT).show();
            }
        });
    }

    /** 获取项目传感器数据（官方模板 GetData 写法） */
    private void getData() {
        String projectId = projectEdit.getText().toString().trim();
        netWorkBusiness.getSensors(projectId, "temp", new NCallBack<BaseResponseEntity<List<SensorInfo>>>(getApplicationContext()) {
            @Override
            protected void onResponse(BaseResponseEntity<List<SensorInfo>> listBaseResponseEntity) {
                if (listBaseResponseEntity.getResultObj() != null && !listBaseResponseEntity.getResultObj().isEmpty()) {
                    SensorInfo sensor = listBaseResponseEntity.getResultObj().get(0);
                    Log.d(TAG, "Sensor Data: " + sensor.getValue());
                    dataText.setText("温度：" + sensor.getValue() + " " + (sensor.getUnit() == null ? "" : sensor.getUnit()));
                }
            }
        });
    }

    /** 发送控制指令（官方模板 SendData 写法） */
    private void control(int value) {
        String projectId = projectEdit.getText().toString().trim();
        netWorkBusiness.control(projectId, "button", value, new NCallBack<BaseResponseEntity>(getApplicationContext()) {
            @Override
            protected void onResponse(BaseResponseEntity baseResponseEntity) {
                Toast.makeText(getApplication(), "控制指令已发送（" + value + "）", Toast.LENGTH_SHORT).show();
            }
        });
    }

    @Override
    public void onClick(View v) {
        if (v.getId() == R.id.loginBtn) {
            signIn();
        } else if (v.getId() == R.id.queryBtn) {
            getData();
        } else if (v.getId() == R.id.controlOnBtn) {
            control(1);
        } else if (v.getId() == R.id.controlOffBtn) {
            control(0);
        }
    }
}
