from copy import deepcopy

import pm4py
from pm4py.objects.petri_net.utils.petri_utils import (
    add_arc_from_to,
    merge,
    remove_transition,
    add_transition,
    add_place,
)


def replace_transition_with_net(
    net, transition_label, sub_net, parent_label, debug=False
):
    if debug:
        pm4py.view_petri_net(
            net, graph_title="Before " + transition_label + " parent " + parent_label
        )
    sub_copy = deepcopy(sub_net)
    transition = next(
        transition
        for transition in net.transitions
        if transition.label == transition_label
    )
    net = merge(net, [sub_copy])
    start_place = next(p for p in sub_copy.places if len(p.in_arcs) == 0)
    start_transition = add_transition(
        net, label="S " + transition_label + "<-" + parent_label
    )
    for t in transition.in_arcs:
        add_arc_from_to(t.source, start_transition, net)
    add_arc_from_to(start_transition, start_place, net)
    end_place = next(p for p in sub_copy.places if len(p.out_arcs) == 0)
    end_transition = add_transition(
        net, label="E " + transition_label + "<-" + parent_label
    )
    add_arc_from_to(end_place, end_transition, net)
    for t in transition.out_arcs:
        add_arc_from_to(end_transition, t.target, net)
    remove_transition(net, transition)
    if debug:
        pm4py.view_petri_net(
            net, graph_title="After " + transition_label + " parent " + parent_label
        )
    return net


def add_parent_label(base, parent_label):
    petri_net = deepcopy(base)
    for transition in petri_net.transitions:
        if not transition.label:
            continue
        transition.label = transition.label + "<-" + parent_label
    for place in petri_net.places:
        if not place.name:
            continue
        place.name = place.name + "<-" + parent_label
    return petri_net


def expand_petri_nets(petri_nets, top_level_activities):
    expanded_petri_nets = dict()
    used_by = dict()

    def expand_petri_net_activities(petri_nets, label, parent_label):
        if parent_label != "":
            if label in used_by:
                used_by[label].append(parent_label)
            else:
                used_by[label] = [parent_label]
        if label in expanded_petri_nets:
            return add_parent_label(expanded_petri_nets[label], parent_label)
        petri_net = petri_nets[label]
        petri_net = deepcopy(petri_net)
        transitions = [
            transition
            for transition in petri_net.transitions
            if transition.label in petri_nets
        ]
        for transition in transitions:
            sub_expanded = expand_petri_net_activities(
                petri_nets, transition.label, label
            )
            petri_net = replace_transition_with_net(
                petri_net, transition.label, sub_expanded, label
            )
        expanded_petri_nets[label] = petri_net
        return add_parent_label(petri_net, parent_label)

    for activity_name in top_level_activities:
        expand_petri_net_activities(petri_nets, activity_name, "")
        petri_net = expanded_petri_nets[activity_name]
        start_transition = add_transition(
            petri_net, "S " + activity_name, label="S " + activity_name
        )
        end_transition = add_transition(
            petri_net, "E " + activity_name, label="E " + activity_name
        )
        start_place = add_place(petri_net, "S " + activity_name + "_place")
        add_arc_from_to(start_place, start_transition, petri_net)
        end_place = add_place(petri_net, "E " + activity_name + "_place")
        add_arc_from_to(end_transition, end_place, petri_net)
        for place in [
            p for p in petri_net.places if len(p.in_arcs) == 0 and p != start_place
        ]:
            add_arc_from_to(start_transition, place, petri_net)
        for place in [
            p for p in petri_net.places if len(p.out_arcs) == 0 and p != end_place
        ]:
            add_arc_from_to(place, end_transition, petri_net)
    for net in expanded_petri_nets.values():
        pm4py.reduce_petri_net_invisibles(net)
    return expanded_petri_nets, used_by
