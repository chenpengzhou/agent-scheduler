import React, { useState, useEffect } from 'react';
import { 
  Layout, Menu, Table, Button, Modal, Form, Input, 
  Select, Tag, Space, message, Card, Row, Col, Statistic 
} from 'antd';
import { 
  PlayCircleOutlined, PauseCircleOutlined, 
  SyncOutlined, CloseCircleOutlined, 
  PlusOutlined, DashboardOutlined, FileTextOutlined 
} from '@ant-design/icons';
import axios from 'axios';

const { Header, Content, Sider } = Layout;
const { Option } = Select;

const API_BASE = '/api/v1';

const statusColors = {
  PENDING: 'default',
  RUNNING: 'processing',
  COMPLETED: 'success',
  FAILED: 'error',
  PAUSED: 'warning',
  CANCELLED: 'default'
};

function App() {
  const [definitions, setDefinitions] = useState([]);
  const [instances, setInstances] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [loading, setLoading] = useState(false);
  const [defModalVisible, setDefModalVisible] = useState(false);
  const [startModalVisible, setStartModalVisible] = useState(false);
  const [selectedDef, setSelectedDef] = useState(null);
  const [form] = Form.useForm();
  const [startForm] = Form.useForm();
  const [currentView, setCurrentView] = useState('dashboard');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [defsRes, instsRes, metricsRes] = await Promise.all([
        axios.get(`${API_BASE}/workflow-definitions`),
        axios.get(`${API_BASE}/workflow-instances`),
        axios.get(`${API_BASE}/workflow-instances/metrics`)
      ]);
      setDefinitions(defsRes.data);
      setInstances(instsRes.data);
      setMetrics(metricsRes.data);
    } catch (error) {
      console.error('Fetch error:', error);
    }
    setLoading(false);
  };

  const handleCreateDefinition = async (values) => {
    try {
      await axios.post(`${API_BASE}/workflow-definitions`, {
        ...values,
        definition_json: {
          steps: values.steps || [
            { id: 'step1', name: 'Step 1', task_def: { id: 'task1', name: 'Task 1' } }
          ]
        }
      });
      message.success('工作流定义创建成功');
      setDefModalVisible(false);
      form.resetFields();
      fetchData();
    } catch (error) {
      message.error('创建失败');
    }
  };

  const handleStartWorkflow = async (values) => {
    try {
      await axios.post(`${API_BASE}/workflow-instances`, {
        definition_id: selectedDef,
        input_data: values.input_data || {},
        triggered_by: 'web'
      });
      message.success('工作流启动成功');
      setStartModalVisible(false);
      startForm.resetFields();
      fetchData();
    } catch (error) {
      message.error('启动失败');
    }
  };

  const handleAction = async (instanceId, action) => {
    try {
      await axios.post(`${API_BASE}/workflow-instances/${instanceId}/${action}`);
      message.success(`工作流${action === 'pause' ? '暂停' : action === 'resume' ? '恢复' : action === 'cancel' ? '取消' : '重试'}成功`);
      fetchData();
    } catch (error) {
      message.error('操作失败');
    }
  };

  const definitionColumns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '版本', dataIndex: 'version', key: 'version' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', 
      render: (text) => new Date(text).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Button 
          type="primary" 
          size="small" 
          icon={<PlayCircleOutlined />}
          onClick={() => {
            setSelectedDef(record.id);
            setStartModalVisible(true);
          }}
        >
          启动
        </Button>
      )
    }
  ];

  const instanceColumns = [
    { title: 'ID', dataIndex: 'id', key: 'id', ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (status) => <Tag color={statusColors[status]}>{status}</Tag> },
    { title: '当前步骤', dataIndex: 'current_step_id', key: 'current_step_id' },
    { title: '触发者', dataIndex: 'triggered_by', key: 'triggered_by' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at',
      render: (text) => new Date(text).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          {record.status === 'RUNNING' && (
            <>
              <Button size="small" icon={<PauseCircleOutlined />} onClick={() => handleAction(record.id, 'pause')}>暂停</Button>
              <Button size="small" danger icon={<CloseCircleOutlined />} onClick={() => handleAction(record.id, 'cancel')}>取消</Button>
            </>
          )}
          {record.status === 'PAUSED' && (
            <Button size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => handleAction(record.id, 'resume')}>恢复</Button>
          )}
          {record.status === 'FAILED' && (
            <Button size="small" icon={<SyncOutlined />} onClick={() => handleAction(record.id, 'retry')}>重试</Button>
          )}
        </Space>
      )
    }
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ color: '#fff', fontSize: 20 }}>Workflow Engine</Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            defaultSelectedKeys={['dashboard']}
            style={{ height: '100%', borderRight: 0 }}
            onClick={(e) => setCurrentView(e.key)}
            items={[
              { key: 'dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
              { key: 'definitions', icon: <FileTextOutlined />, label: '工作流定义' },
              { key: 'instances', icon: <PlayCircleOutlined />, label: '工作流实例' },
            ]}
          />
        </Sider>
        <Layout style={{ padding: '24px' }}>
          <Content style={{ background: '#fff', padding: 24, margin: 0, minHeight: 280 }}>
            {currentView === 'dashboard' && (
              <div>
                <Row gutter={16}>
                  <Col span={6}>
                    <Card>
                      <Statistic title="总定义数" value={metrics.total_definitions || 0} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic title="总实例数" value={metrics.total_instances || 0} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic title="运行中" value={metrics.status_counts?.RUNNING || 0} />
                    </Card>
                  </Col>
                  <Col span={6}>
                    <Card>
                      <Statistic title="已完成" value={metrics.status_counts?.COMPLETED || 0} />
                    </Card>
                  </Col>
                </Row>
              </div>
            )}

            {currentView === 'definitions' && (
              <div>
                <div style={{ marginBottom: 16 }}>
                  <Button type="primary" icon={<PlusOutlined />} onClick={() => setDefModalVisible(true)}>
                    创建工作流
                  </Button>
                </div>
                <Table 
                  columns={definitionColumns} 
                  dataSource={definitions} 
                  rowKey="id" 
                  loading={loading}
                />
              </div>
            )}

            {currentView === 'instances' && (
              <div>
                <div style={{ marginBottom: 16 }}>
                  <Button onClick={fetchData}>刷新</Button>
                </div>
                <Table 
                  columns={instanceColumns} 
                  dataSource={instances} 
                  rowKey="id" 
                  loading={loading}
                />
              </div>
            )}
          </Content>
        </Layout>
      </Layout>

      <Modal
        title="创建工作流定义"
        open={defModalVisible}
        onCancel={() => setDefModalVisible(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleCreateDefinition} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="version" label="版本" initialValue="1.0">
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="启动工作流"
        open={startModalVisible}
        onCancel={() => setStartModalVisible(false)}
        onOk={() => startForm.submit()}
      >
        <Form form={startForm} onFinish={handleStartWorkflow} layout="vertical">
          <Form.Item name="input_data" label="输入数据 (JSON)">
            <Input.TextArea rows={4} placeholder='{"key": "value"}' />
          </Form.Item>
        </Form>
      </Modal>
    </Layout>
  );
}

export default App;
