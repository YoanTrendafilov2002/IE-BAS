#include "StateMachine.h"
namespace irrigation::plant { void StateMachine::transition_to(NodeState state) { state_ = state; } NodeState StateMachine::current() const { return state_; } }
