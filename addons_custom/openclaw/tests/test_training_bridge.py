from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.openclaw.training.bridge import OpenClawTrainingBridge


@tagged('post_install', '-at_install')
class TestOpenClawTrainingBridge(TransactionCase):
    def setUp(self):
        super().setUp()
        self.policy = self.env['openclaw.policy'].create({
            'name': 'Training Policy',
            'key': 'training_policy',
            'sequence': 1,
            'allow_read_db': True,
        })
        self.session = self.env['openclaw.chat.session'].create({
            'name': 'Training Session',
        })
        self.user_message = self.env['openclaw.chat.message'].create({
            'session_id': self.session.id,
            'role': 'user',
            'content': 'Create a partner for Acme',
        })
        self.assistant_message = self.env['openclaw.chat.message'].create({
            'session_id': self.session.id,
            'role': 'assistant',
            'content': 'I can do that.',
        })
        self.request = self.env['openclaw.request'].create({
            'name': 'Create partner',
            'instruction': 'Create the partner',
            'policy_id': self.policy.id,
            'session_id': self.session.id,
            'message_id': self.assistant_message.id,
            'origin': 'chat_suggestion',
            'action_type': 'odoo_write',
            'state': 'executed',
            'approval_required': False,
        })

    def test_build_episode(self):
        bridge = OpenClawTrainingBridge()
        payload = self.session._session_payload(include_messages=True)
        payload['policy_context'] = self.session._build_policy_context()
        episode = bridge.build_episode(payload)

        self.assertEqual(episode.session_id, self.session.id)
        self.assertEqual(len(episode.turns), 1)
        self.assertGreaterEqual(episode.reward, 1.0)
        record = episode.to_agentlightning_record()
        self.assertEqual(record['task_id'], f'openclaw-session-{self.session.id}')
        self.assertEqual(record['turns'][0]['requests'][0]['id'], self.request.id)

    def test_build_dataset_returns_records(self):
        bridge = OpenClawTrainingBridge()
        payload = self.session._session_payload(include_messages=True)
        payload['policy_context'] = self.session._build_policy_context()
        dataset = bridge.build_dataset([payload])

        self.assertEqual(len(dataset), 1)
        self.assertEqual(dataset[0].summary['request_count'], 1)
