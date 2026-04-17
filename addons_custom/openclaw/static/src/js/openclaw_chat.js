/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class OpenClawChatAction extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            sessions: [],
            activeSession: null,
            messages: [],
            draft: "",
            loading: true,
            sending: false,
        });

        this.refreshSessions = async () => {
            this.state.sessions = await this.orm.call("openclaw.chat.session", "rpc_list_sessions", []);
        };

        this.selectSession = async (sessionId) => {
            this.state.loading = true;
            try {
                const session = await this.orm.call("openclaw.chat.session", "rpc_get_session", [sessionId]);
                this.state.activeSession = session;
                this.state.messages = session.messages || [];
                await this.refreshSessions();
            } finally {
                this.state.loading = false;
            }
        };

        this.createSession = async () => {
            this.state.loading = true;
            try {
                const session = await this.orm.call("openclaw.chat.session", "rpc_create_session", []);
                await this.refreshSessions();
                await this.selectSession(session.id);
            } catch (error) {
                this.notification.add(_t("Unable to create a new chat session."), { type: "danger" });
                throw error;
            } finally {
                this.state.loading = false;
            }
        };

        this.sendMessage = async () => {
            const content = this.state.draft.trim();
            if (!content || this.state.sending) {
                return;
            }

            if (!this.state.activeSession) {
                await this.createSession();
            }

            const sessionId = this.state.activeSession.id;
            this.state.sending = true;
            this.state.draft = "";

            try {
                const result = await this.orm.call("openclaw.chat.session", "rpc_send_message", [sessionId, content]);
                this.state.activeSession = result.session;
                this.state.messages = result.session.messages || [];
                await this.refreshSessions();
            } catch (error) {
                this.notification.add(_t("OpenClaw could not send the message."), { type: "danger" });
                this.state.draft = content;
            } finally {
                this.state.sending = false;
            }
        };

        this.onDraftKeydown = async (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                await this.sendMessage();
            }
        };

        onWillStart(async () => {
            await this.refreshSessions();
            if (this.state.sessions.length) {
                await this.selectSession(this.state.sessions[0].id);
            } else {
                await this.createSession();
            }
        });
    }
}

OpenClawChatAction.template = "openclaw.OpenClawChatAction";

registry.category("actions").add("openclaw_chat_action", OpenClawChatAction);