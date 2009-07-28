""" Finite state machine, useful for workflow-like features, based on
Skip Montanaro's FSM from
http://wiki.python.org/moin/FiniteStateMachine (ancient but simple #
and useful!)"""
from repoze.bfg.workflow.interfaces import IStateMachine
from zope.interface import implements

_marker = object()

class StateMachineError(Exception):
    """ Invalid input to finite state machine"""

class StateMachine(object):
    """ Finite state machine featuring transition actions.

    The class stores a sequence of transition dictionaries.

    When a (state, transition_name) search is performed via ``execute``:

      * an exact match is checked first,
      * (state, None) is checked next.

    The callback must be of the following form:
    * callback(context, transition_info)

    ``transition_info`` passed to the transition funciton is a
    dictionary containing transition information.

    It is recommended that all transition functions be module level
    callables to facilitate issues related to StateMachine
    persistence.
    """
    implements(IStateMachine)
    
    def __init__(self, state_attr, transitions=None, initial_state=None,
                 initializer=None):
        """
        o state_attr - attribute name where a given object's current
                       state will be stored (object is responsible for
                       persisting)
                       
        o transitions - initial list of transition dictionaries

        o initial_state - initial state for any object using this
                          state machine

        o initializer - callback function that accepts a context
          to initialize a context object to the initial state
        """
        if transitions is None:
            transitions = []
        self._transitions = transitions
        self._state_data = {}
        self._state_order = []
        self.state_attr = state_attr
        self.initializer = initializer
        self.initial_state = initial_state

    def add_state_info(self, state_name, **kw):
        if not state_name in self._state_order:
            self._state_order.append(state_name)
        if not state_name in self._state_data:
            self._state_data[state_name] = {}
        self._state_data[state_name].update(kw)

    def add_transition(self, transition_name, from_state, to_state,
                       callback, **kw):
        """ Add a transition to the FSM.  ``**kw`` must not contain
        any of the keys ``from_state``, ``name``, ``to_state``, or
        ``callback``; these are reserved for internal use."""
        self.add_state_info(from_state)
        self.add_state_info(to_state)
        transition = kw
        transition['name'] = transition_name
        transition['from_state'] = from_state
        transition['to_state'] = to_state
        transition['callback'] = callback
        self._transitions.append(transition)

    def execute(self, context, transition_name, guards=()):
        """ Execute a transition """
        state = getattr(context, self.state_attr, _marker) 
        if state is _marker:
            state = self.initial_state
        si = (state, transition_name)

        found = None
        for transition in self._transitions:
            match = (transition['from_state'], transition['name'])
            if match == si:
                found = transition
                break

        if found is None:
            raise StateMachineError(
                'No transition from %r using transition %r'
                % (state, transition_name))

        if guards:
            for guard in guards:
                guard(context, found)

        callback = found['callback']
        if callback is not None:
            callback(context, found)
        to_state = found['to_state']
        setattr(context, self.state_attr, to_state)

    def state_of(self, context):
        state = getattr(context, self.state_attr, self.initial_state)
        return state

    def transitions(self, context, from_state=None):
        if from_state is None:
            from_state = self.state_of(context)
        transitions = [transition for transition in self._transitions
                       if from_state == transition['from_state']]
        return transitions

    def transition_to_state(self, context, to_state, guards=(), skip_same=True):
        from_state = self.state_of(context)
        if (from_state == to_state) and skip_same:
            return
        state_info = self.state_info(context)
        for info in state_info:
            if info['name'] == to_state:
                transitions = info['transitions']
                if transitions:
                    transition = transitions[0]
                    self.execute(context, transition['name'], guards)
                    return
        raise StateMachineError('No transition from state %r to state %r'
                % (from_state, to_state))

    def state_info(self, context, from_state=None):
        context_state = self.state_of(context)
        if from_state is None:
            from_state = context_state

        L = []

        for state_name in self._state_order:
            D = {'name':state_name, 'transitions':[]}
            state_data = self._state_data[state_name]
            D['data'] = state_data
            D['initial'] = state_name == self.initial_state
            D['current'] = state_name == context_state
            title = state_data.get('title', state_name)
            D['title'] = title
            for transition in self._transitions:
                if (transition['from_state'] == from_state and
                    transition['to_state'] == state_name):
                    transitions = D['transitions']
                    transitions.append(transition)
            L.append(D)

        return L

    def initialize(self, context):
        setattr(context, self.state_attr, self.initial_state)
        if self.initializer is not None:
            self.initializer(context)
            
        
