# 1 linkedin爬虫
## 1.1 linkedin模拟登录接口
#### 接口：
> `/linkedin/login`

#### HTTP请求方式：
> `POST`

#### 请求参数：
|参数名|类型|必需|描述|
|---|---|---|---|
|`username`| string | 是 | 用户名|
|`password`| string | 是 | 密码|
#### 返回字段：
|返回字段|字段类型|说明 |
|:----- |:------|:----------------------------- |
|`status`   |int |返回结果状态 |
|`error`|string |错误信息 |
|`data`|object|正确信息|

## 1.2 linkedin验证码验证
#### 接口：
> `/linkedin/verify`

#### HTTP请求方式：
> `POST`

#### 请求参数：
|参数名|类型|必需|描述|
|---|---|---|---|
|`username`| string | 是 | 用户名|
|`vCode`| string | 是 |验证码|
#### 返回字段：
|返回字段|字段类型|说明 |
|:----- |:------|:----------------------------- |
|`status`   |int |返回结果状态 |
|`error`|string |错误信息 |
|`data`|object|正确信息|

# 状态码
|状态码|返回信息|
|:----- |:------|
|`1200` | 登录成功信息 |
|`1401`   |密码或账号错误！|
|`1402`   |被拒绝登录！|
|`1403`   |需要输入验证码！|
|`1404`   |验证码无效！|
|`1405`   |登录超时！|