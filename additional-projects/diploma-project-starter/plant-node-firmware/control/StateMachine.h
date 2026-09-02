#pragma once

namespace irrigation::plant {
enum class NodeState { Boot, LoadConfig, JoinMesh, SelfTest, Measure, SafetyCheck, Decide, WaterOrSkip, Settle, ReportToFrontNode, SleepOrWait };
class StateMachine { public: void transition_to(NodeState state); NodeState current() const; private: NodeState state_ = NodeState::Boot; };
}  // namespace irrigation::plant
