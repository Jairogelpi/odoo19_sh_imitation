/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

class ChatSidebar extends Component {}
ChatSidebar.template = "openclaw.ChatSidebar";
ChatSidebar.props = {
    sessions: Array,
    activeSessionId: { type: [Number, Boolean], optional: true },
    onSelect: Function,
    onCreate: Function,
};

class ChatHeader extends Component {}
ChatHeader.template = "openclaw.ChatHeader";
ChatHeader.props = {
    session: { type: Object, optional: true },
};

class ActionCard extends Component {}
ActionCard.template = "openclaw.ActionCard";
ActionCard.props = {
    request: Object,
    disableApprove: { type: Boolean, optional: true },
    isApproving: { type: Boolean, optional: true },
    onApprove: Function,
    onReject: Function,
    onViewDetail: Function,
};

class ChatMessages extends Component {}
ChatMessages.template = "openclaw.ChatMessages";
ChatMessages.components = { ActionCard };
ChatMessages.props = {
    messages: Array,
    loading: Boolean,
    sending: Boolean,
    approvingRequestId: { type: [Number, null], optional: true },
    sessionHasApproving: Boolean,
    onApprove: Function,
    onReject: Function,
    onViewDetail: Function,
};

class ChatComposer extends Component {
    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.props.onSend();
        }
    }
}
ChatComposer.template = "openclaw.ChatComposer";
ChatComposer.props = {
    draft: String,
    sending: Boolean,
    onDraftChange: Function,
    onSend: Function,
};

class RequestDrawer extends Component {}
RequestDrawer.template = "openclaw.RequestDrawer";
RequestDrawer.props = {
    request: { type: Object, optional: true },
    loading: Boolean,
    onClose: Function,
};

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
            sidebarOpen: false,
            approvingRequestId: null,
            drawerRequestId: null,
            drawerRequest: null,
            drawerLoading: false,
        });

        this.refreshSessions = async () => {
            this.state.sessions = await this.orm.call(
                "openclaw.chat.session", "rpc_list_sessions", [],
            );
        };

        this.selectSession = async (sessionId) => {
            this.state.loading = true;
            try {
                const session = await this.orm.call(
                    "openclaw.chat.session", "rpc_get_session", [sessionId],
                );
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
                const session = await this.orm.call(
                    "openclaw.chat.session", "rpc_create_session", [],
                );
                await this.refreshSessions();
                await this.selectSession(session.id);
            } catch (error) {
                this.notification.add(_t("Unable to create a new chat session."), { type: "danger" });
                throw error;
            } finally {
                this.state.loading = false;
            }
        };

        this.setDraft = (value) => {
            this.state.draft = value;
        };

        this.sendMessage = async () => {
            const content = this.state.draft.trim();
            if (!content || this.state.sending) return;
            if (!this.state.activeSession) {
                await this.createSession();
            }
            const sessionId = this.state.activeSession.id;
            this.state.sending = true;
            this.state.draft = "";
            try {
                const result = await this.orm.call(
                    "openclaw.chat.session", "rpc_send_message",
                    [sessionId, content],
                );
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

        this.approveRequest = async (requestId) => {
            if (this.state.approvingRequestId !== null) return;
            this.state.approvingRequestId = requestId;
            try {
                const updated = await this.orm.call(
                    "openclaw.chat.session", "rpc_approve_request",
                    [requestId],
                );
                this._replaceRequestInMessages(updated);
                if (updated.state === "failed") {
                    this.notification.add(_t("OpenClaw could not execute the action."), { type: "danger" });
                }
            } catch (error) {
                this.notification.add(_t("Approval failed."), { type: "danger" });
            } finally {
                this.state.approvingRequestId = null;
            }
        };

        this.rejectRequest = async (requestId) => {
            try {
                const updated = await this.orm.call(
                    "openclaw.chat.session", "rpc_reject_request",
                    [requestId],
                );
                this._replaceRequestInMessages(updated);
            } catch (error) {
                this.notification.add(_t("Rejection failed."), { type: "danger" });
            }
        };

        this.openRequestDetail = async (requestId) => {
            this.state.drawerRequestId = requestId;
            this.state.drawerRequest = null;
            this.state.drawerLoading = true;
            try {
                const detail = await this.orm.call(
                    "openclaw.chat.session", "rpc_get_request_detail",
                    [requestId],
                );
                this.state.drawerRequest = detail;
            } catch (error) {
                this.notification.add(_t("Could not load request details."), { type: "danger" });
                this.state.drawerRequestId = null;
            } finally {
                this.state.drawerLoading = false;
            }
        };

        this.closeDrawer = () => {
            this.state.drawerRequestId = null;
            this.state.drawerRequest = null;
        };

        this._replaceRequestInMessages = (updated) => {
            for (const message of this.state.messages) {
                if (!message.requests) continue;
                const idx = message.requests.findIndex((r) => r.id === updated.id);
                if (idx >= 0) {
                    message.requests[idx] = { ...message.requests[idx], ...updated };
                    return;
                }
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
OpenClawChatAction.components = {
    ChatSidebar,
    ChatHeader,
    ChatMessages,
    ChatComposer,
    RequestDrawer,
};

registry.category("actions").add("openclaw_chat_action", OpenClawChatAction);
